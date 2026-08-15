import base64
import math
import os
import random
import re
import sqlite3
import time
import uuid
import secrets
import threading
from collections import defaultdict, deque
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

CUSTOM_DOMAIN = ""  # Leave blank to auto-detect
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(BASE_DIR, "saved_scripts")
DB_PATH = os.path.join(BASE_DIR, "database.db")

# Runtime limits
MAX_SOURCE_BYTES = 1024 * 1024       # 1 MiB per compilation
SCRIPT_TTL = 15 * 60                  # 15 minutes
CLEANUP_INTERVAL = 60                 # 1 minute
RATE_WINDOW = 60                      # 1 minute
RATE_LIMIT = 30                       # compilations/IP/minute

os.makedirs(SAVED_DIR, exist_ok=True)

SCRIPT_CACHE = {}
CACHE_LOCK = threading.RLock()
RATE_STATE = defaultdict(deque)
RATE_LOCK = threading.RLock()


def cleanup_expired_scripts():
    """Thread-safe TTL cleanup for generated scripts."""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        cutoff = time.time() - SCRIPT_TTL

        with CACHE_LOCK:
            expired = [
                token for token, data in SCRIPT_CACHE.items()
                if data.get("created_at", 0) < cutoff
            ]

            for token in expired:
                SCRIPT_CACHE.pop(token, None)
                file_path = os.path.join(SAVED_DIR, f"{token}.lua")
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except OSError:
                    pass


threading.Thread(
    target=cleanup_expired_scripts,
    name="classicfuscator-cleanup",
    daemon=True,
).start()


def init_db():
    """Keep the existing database initialized for backwards compatibility."""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS scripts
               (token TEXT PRIMARY KEY, code TEXT, created_at REAL)"""
        )
        conn.commit()
    finally:
        conn.close()


init_db()


def gen_id(length=None):
    """Generate a build-specific identifier without relying on a mutable default."""
    if length is None:
        length = secrets.randbelow(7) + 12
    # Keep identifiers Lua-safe while avoiding the very obvious I/l/1/O/0-only pattern.
    first = random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
    rest = "".join(
        random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
        for _ in range(max(1, length - 1))
    )
    return first + rest


def _lua_lex_number_safe(source):
    """
    Transform integer/decimal literals without touching:
      - quoted strings
      - long strings
      - line comments
      - block comments
      - identifiers
      - hexadecimal literals
    This is intentionally a small lexer, not a full Lua parser.
    """
    out = []
    i = 0
    n = len(source)

    def read_quoted(pos, quote):
        j = pos + 1
        while j < n:
            if source[j] == "\\\\":
                j += 2
                continue
            if source[j] == quote:
                return j + 1
            j += 1
        return n

    def read_long_bracket(pos):
        # Supports Lua's [=[ ... ]=] style long strings/comments.
        m = re.match(r"\\[(=*)\\[", source[pos:])
        if not m:
            return None
        eq = m.group(1)
        close = "]" + eq + "]"
        end_pos = source.find(close, pos + len(m.group(0)))
        return n if end_pos < 0 else end_pos + len(close)

    while i < n:
        # Quoted strings
        if source[i] in ("'", '"'):
            j = read_quoted(i, source[i])
            out.append(source[i:j])
            i = j
            continue

        # Long strings / comments
        long_end = read_long_bracket(i)
        if long_end is not None:
            out.append(source[i:long_end])
            i = long_end
            continue

        # Comments
        if source.startswith("--", i):
            long_comment_end = read_long_bracket(i + 2)
            if long_comment_end is not None:
                out.append(source[i:long_comment_end])
                i = long_comment_end
                continue

            line_end = source.find("\\n", i + 2)
            if line_end < 0:
                out.append(source[i:])
                break
            out.append(source[i:line_end])
            i = line_end
            continue

        # Decimal integer/float. Avoid identifiers and hex literals.
        if source[i].isdigit() and not (
            i > 0 and (source[i - 1].isalnum() or source[i - 1] == "_")
        ):
            m = re.match(
                r"(?:0[xX][0-9a-fA-F]+|(?:\\d+\\.\\d*|\\d*\\.\\d+|\\d+)(?:[eE][+-]?\\d+)?)",
                source[i:],
            )
            if m:
                token = m.group(0)
                if not token.lower().startswith("0x") and token.isdigit():
                    value = int(token)
                    offset = secrets.randbelow(9000) + 1000
                    out.append(f"({value + offset} - {offset})")
                else:
                    out.append(token)
                i += len(token)
                continue

        out.append(source[i])
        i += 1

    return "".join(out)


def strip_lua_comments_safe(source):
    """Remove comments without destroying strings or long-string contents."""
    out = []
    i = 0
    n = len(source)

    while i < n:
        if source[i] in ("'", '"'):
            quote = source[i]
            j = i + 1
            while j < n:
                if source[j] == "\\\\":
                    j += 2
                    continue
                if source[j] == quote:
                    j += 1
                    break
                j += 1
            out.append(source[i:j])
            i = j
            continue

        m = re.match(r"\\[(=*)\\[", source[i:])
        if m:
            eq = m.group(1)
            close = "]" + eq + "]"
            end = source.find(close, i + len(m.group(0)))
            end = n if end < 0 else end + len(close)
            out.append(source[i:end])
            i = end
            continue

        if source.startswith("--", i):
            m = re.match(r"--\\[(=*)\\[", source[i:])
            if m:
                eq = m.group(1)
                close = "]" + eq + "]"
                end = source.find(close, i + len(m.group(0)))
                i = n if end < 0 else end + len(close)
            else:
                end = source.find("\\n", i + 2)
                i = n if end < 0 else end
            out.append("\\n" if i < n and source[i] == "\\n" else "")
            continue

        out.append(source[i])
        i += 1

    return "".join(out)


def inner_obfuscate(lua_code):
    """Lexically safe lightweight source transformation."""
    without_comments = strip_lua_comments_safe(lua_code)
    return _lua_lex_number_safe(without_comments)


# ==============================================================================
# 2. RC4 STREAM CIPHER & CUSTOM BASE-N ENCODING
# ==============================================================================
def rc4_encrypt(data_string, key_string):
    """Legacy compatibility cipher used by the existing runtime format."""
    S = list(range(256))
    j = 0
    out = []
    
    # Key-scheduling algorithm (KSA)
    for i in range(256):
        j = (j + S[i] + ord(key_string[i % len(key_string)])) % 256
        S[i], S[j] = S[j], S[i]
        
    # Pseudo-random generation algorithm (PRGA)
    i = j = 0
    for char in data_string:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(chr(ord(char) ^ S[(S[i] + S[j]) % 256]))
        
    return "".join(out)

def custom_base64_encode(data_string):
    """Generates a totally randomized Base64 alphabet per script."""
    standard_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    custom_alphabet = list(standard_alphabet)
    random.shuffle(custom_alphabet)
    custom_alphabet_str = "".join(custom_alphabet)
    
    # Standard b64 encode
    import base64
    b64_std = base64.b64encode(data_string.encode('latin1')).decode('ascii')
    
    # Translate standard to custom
    trans = str.maketrans(standard_alphabet, custom_alphabet_str)
    return b64_std.translate(trans), custom_alphabet_str

# ==============================================================================
# 3. CONTROL FLOW FLATTENED VM GENERATOR
# ==============================================================================
def build_enterprise_vm(raw_code, settings):
    # 1. Pre-obfuscate raw code
    inner_code = inner_obfuscate(raw_code)
    
    # 2. Generate random RC4 key
    rc4_key = gen_id(32)
    
    # 3. Encrypt payload with RC4
    encrypted_payload = rc4_encrypt(inner_code, rc4_key)
    
    # 4. Encode with Custom Alphabet
    encoded_payload, custom_alphabet = custom_base64_encode(encrypted_payload)
    
    # Random Variables
    v_env = gen_id()
    v_blob = gen_id()
    v_alphabet = gen_id()
    v_decode = gen_id()
    v_rc4 = gen_id()
    v_state = gen_id()
    v_loader = gen_id()
    v_anti = gen_id()

    anti_tamper = ""
    if settings.get("antihook", True):
        anti_tamper = f"""
        local function {v_anti}()
            local _g = getfenv or getgenv or _G
            local _l = _g().loadstring or loadstring or load
            if type(_l) ~= "function" then return false end
            
            -- debug.getinfo check to detect Hooking/Dumping
            if type(debug) == "table" and type(debug.getinfo) == "function" then
                local s, i = pcall(debug.getinfo, _l)
                if s and type(i) == "table" then
                    if i.what ~= "C" then return false end -- Hooked by a Lua script!
                end
            end
            return true
        end
        if not {v_anti}() then return end
        """

    # Control Flow Flattening (CFF) States
    states = list(range(1, 6))
    random.shuffle(states)
    s_init, s_decode, s_rc4, s_compile, s_exec = states

    vm_lua = f"""
local function __START()
    {anti_tamper}
    local {v_state} = {s_init}
    local {v_blob} = "{encoded_payload}"
    local {v_alphabet} = "{custom_alphabet}"
    local _k = "{rc4_key}"
    local _res, _func
    
    local {v_loader} = (type(getgenv) == "function" and getgenv().loadstring) or loadstring or load
    if not {v_loader} then return end

    -- Custom BaseN Decoder
    local function {v_decode}(data, alpha)
        data = string.gsub(data, '[^'..alpha..'=]', '')
        local res = {{}}
        for i = 1, #data, 4 do
            local n = 0
            for j = 0, 3 do
                local c = string.sub(data, i+j, i+j)
                if c ~= '=' then
                    local p = string.find(alpha, c, 1, true)
                    if p then n = n + (p - 1) * (64 ^ (3 - j)) end
                end
            end
            for j = 2, 0, -1 do
                if string.sub(data, i + 3 - j, i + 3 - j) ~= '=' then
                    table.insert(res, string.char(math.floor(n / (256 ^ j)) % 256))
                end
            end
        end
        return table.concat(res)
    end

    -- RC4 Algorithm
    local function {v_rc4}(data, key)
        local s = {{}}
        for i = 0, 255 do s[i] = i end
        local j = 0
        for i = 0, 255 do
            j = (j + s[i] + string.byte(key, (i % #key) + 1)) % 256
            s[i], s[j] = s[j], s[i]
        end
        local res = {{}}
        local i = 0
        j = 0
        for idx = 1, #data do
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            table.insert(res, string.char(bit32 and bit32.bxor(string.byte(data, idx, idx), s[(s[i] + s[j]) % 256]) or (function(a,b) local r,p=0,1 while a>0 or b>0 do if a%2~=b%2 then r=r+p end a,b,p=math.floor(a/2),math.floor(b/2),p*2 end return r end)(string.byte(data, idx, idx), s[(s[i] + s[j]) % 256])))
        end
        return table.concat(res)
    end

    -- Control Flow Flattened Dispatcher
    while {v_state} ~= 0 do
        if {v_state} == {s_init} then
            {v_state} = {s_decode}
        elseif {v_state} == {s_decode} then
            _res = {v_decode}({v_blob}, {v_alphabet})
            {v_blob} = nil -- Clear memory
            {v_state} = {s_rc4}
        elseif {v_state} == {s_rc4} then
            _res = {v_rc4}(_res, _k)
            _k = nil -- Clear memory
            {v_state} = {s_compile}
        elseif {v_state} == {s_compile} then
            local f, err = {v_loader}(_res)
            _res = nil -- Clear memory
            if f then 
                _func = f 
                {v_state} = {s_exec}
            else 
                {v_state} = 0 
            end
        elseif {v_state} == {s_exec} then
            pcall(_func)
            {v_state} = 0
        end
    end
end
pcall(__START)
"""
    return vm_lua.strip()

# ==============================================================================
# 4. LIGHT THEME DASHBOARD UI (UNCHANGED)
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator Enterprise</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #f2f4f8; color: #1e293b; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03); width: 100%; max-width: 560px; padding: 36px 32px; border: 1px solid #eef0f4; }
        h1 { font-size: 28px; font-weight: 700; color: #1a1a1a; margin: 0 0 20px 0; letter-spacing: -0.3px; }
        
        .tab-nav { display: flex; gap: 8px; background: #f1f5f9; padding: 4px; border-radius: 12px; margin-bottom: 24px; }
        .tab-btn { flex: 1; padding: 10px 16px; border: none; background: transparent; color: #64748b; font-size: 14px; font-weight: 600; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; }
        .tab-btn.active { background: #ffffff; color: #0070f3; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .file-upload-box { border: 2px dashed #0070f3; border-radius: 12px; padding: 22px 20px; background-color: #ffffff; margin-bottom: 18px; text-align: center; cursor: pointer; transition: all 0.2s ease; }
        .file-upload-box:hover { background-color: #f0f7ff; border-color: #0052cc; }
        .file-upload-title { font-size: 15px; font-weight: 700; color: #1a1a1a; margin-bottom: 4px; display: block; }
        .file-upload-subtext { font-size: 13px; color: #64748b; margin: 0; }
        .or-text { font-size: 14px; font-weight: 500; color: #1e293b; margin-bottom: 10px; }
        
        textarea { width: 100%; height: 160px; border: 1px solid #dcdfe6; border-radius: 12px; padding: 14px; font-size: 13.5px; font-family: monospace; outline: none; background-color: #ffffff; color: #1e293b; transition: border-color 0.2s ease; resize: vertical; }
        textarea:focus { border-color: #0070f3; box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.12); }
        
        .btn { width: 100%; padding: 14px; background-color: #0070f3; color: #ffffff; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 18px; transition: background-color 0.2s ease; box-shadow: 0 4px 12px rgba(0, 112, 243, 0.2); }
        .btn:hover { background-color: #005bb5; }
        
        .output-container { margin-top: 22px; display: none; }
        .loader-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; }
        .section-label { font-size: 13px; font-weight: 600; color: #0070f3; margin-bottom: 8px; display: block; }
        .loader-text { width: 100%; height: 48px; background: #ffffff; border: 1px solid #dcdfe6; border-radius: 8px; color: #1e293b; font-family: monospace; font-size: 12.5px; padding: 12px; white-space: nowrap; overflow-x: auto; resize: none; }

        .setting-group { margin-bottom: 18px; background: #f8fafc; padding: 14px 16px; border-radius: 12px; border: 1px solid #eef2f6; display: flex; justify-content: space-between; align-items: center; }
        .setting-title { font-size: 14px; font-weight: 600; color: #1e293b; }
        .setting-desc { font-size: 12px; color: #64748b; margin-top: 4px; }
        
        .switch { position: relative; display: inline-block; width: 44px; height: 24px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: .3s; border-radius: 24px; }
        .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
        input:checked + .slider { background-color: #0070f3; }
        input:checked + .slider:before { transform: translateX(20px); }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator V2</h1>

        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('obfuscatorTab', this)">Obfuscator</button>
            <button class="tab-btn" onclick="switchTab('settingsTab', this)">Settings</button>
        </div>

        <div id="obfuscatorTab" class="tab-content active">
            <div class="file-upload-box" id="dropZone" onclick="document.getElementById('luaFileInput').click()">
                <span class="file-upload-title">Upload a Lua File:</span>
                <p class="file-upload-subtext" id="dropSubtext">Click to choose or drag & drop file (.lua, .txt)</p>
                <input type="file" id="luaFileInput" accept=".lua,.luau,.txt" onchange="handleFileSelect(event)" style="display: none;">
            </div>

            <div class="or-text">Or paste your Roblox Lua script here:</div>
            <textarea id="input" placeholder="print('Testing Classicfuscator Enterprise!')"></textarea>

            <button class="btn" id="submitBtn" onclick="obfuscate()">Start Obfuscation</button>

            <div class="output-container" id="outputWrapper">
                <div class="loader-box">
                    <span class="section-label">Roblox Loader Script (1-Liner):</span>
                    <textarea id="loaderOutput" class="loader-text" readonly></textarea>
                    <button class="btn" id="copyBtn" style="background-color: #334155; color: #ffffff; box-shadow: none; margin-top: 10px;" onclick="copyLoader()">Copy Loader</button>
                </div>
            </div>
        </div>

        <div id="settingsTab" class="tab-content">
            <div class="setting-group">
                <div>
                    <div class="setting-title">Encrypted Payload & Custom BaseN</div>
                    <div class="setting-desc">Automatically enabled as an additional encoding layer.</div>
                </div>
                <label class="switch"><input type="checkbox" checked disabled><span class="slider"></span></label>
            </div>

            <div class="setting-group">
                <div>
                    <div class="setting-title">Runtime Integrity Checks</div>
                    <div class="setting-desc">Adds a lightweight runtime integrity check.</div>
                </div>
                <label class="switch"><input type="checkbox" id="cfgAntiHook" checked><span class="slider"></span></label>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
        }

        function handleFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('input').value = e.target.result;
                    document.getElementById('dropSubtext').innerText = "Loaded: " + files[0].name;
                };
                reader.readAsText(files[0]);
            }
        }

        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const loaderArea = document.getElementById('loaderOutput');
            const submitBtn = document.getElementById('submitBtn');
            
            if (!inputCode.trim()) return;

            const settings = {
                antihook: document.getElementById('cfgAntiHook').checked
            };

            outputWrapper.style.display = "block";
            loaderArea.value = "-- Compiling Polymorphic VM...";
            submitBtn.innerText = "Processing...";

            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 30000);

                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                    body: JSON.stringify({ code: inputCode, settings: settings }),
                    signal: controller.signal
                });
                clearTimeout(timeout);

                const contentType = response.headers.get('content-type') || '';
                let data = {};
                if (contentType.includes('application/json')) {
                    data = await response.json();
                } else {
                    const text = await response.text();
                    data = { error: text || `Server returned HTTP ${response.status}` };
                }

                if (response.ok && data.loader) {
                    loaderArea.value = data.loader;
                } else {
                    loaderArea.value = `-- Server error (${response.status}): ${data.error || 'Compilation failed.'}`;
                }
            } catch (err) {
                if (err && err.name === 'AbortError') {
                    loaderArea.value = '-- Error: Server request timed out after 30 seconds.';
                } else {
                    loaderArea.value = '-- Network error: ' + (err && err.message ? err.message : 'Could not connect to server.');
                }
            } finally {
                submitBtn.innerText = "Start Obfuscation";
            }
        }

        function copyLoader() {
            const loaderArea = document.getElementById('loaderOutput');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            document.getElementById('copyBtn').innerText = "Copied to Clipboard!";
            setTimeout(() => { document.getElementById('copyBtn').innerText = "Copy Loader"; }, 2000);
        }
    </script>
</body>
</html>
"""

PROTECTED_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Protected By Classicfuscator</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #f2f4f8; color: #1e293b; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); width: 100%; max-width: 440px; padding: 40px 28px; border: 1px solid #eef0f4; text-align: center; }
        h1 { font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 0 0 10px 0; }
        p { font-size: 15px; color: #64748b; margin: 0; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Protected By Classicfuscator V2</h1>
        <p>Cannot be shown publicly.</p>
    </div>
</body>
</html>
"""

def _client_ip():
    # ProxyFix is already configured above; request.remote_addr is the normalized value.
    return request.remote_addr or "unknown"


def _rate_limit_ok(ip):
    now = time.time()
    cutoff = now - RATE_WINDOW
    with RATE_LOCK:
        q = RATE_STATE[ip]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False
        q.append(now)
        return True


def _validate_source(raw_code):
    if not isinstance(raw_code, str):
        return None, "Source must be text."

    raw_bytes = raw_code.encode("utf-8", errors="strict")
    if not raw_bytes.strip():
        return None, "Empty input."
    if len(raw_bytes) > MAX_SOURCE_BYTES:
        return None, f"Source exceeds the {MAX_SOURCE_BYTES // 1024} KiB limit."

    return raw_code, None



@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    app.logger.exception("Unhandled server error")
    return jsonify({
        "success": False,
        "error": f"Server error: {type(exc).__name__}"
    }), 500

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/health", methods=["GET"])
def health():
    """Simple Render/container health endpoint."""
    return jsonify({"status": "ok", "service": "Classicfuscator", "version": "V3"})

@app.route("/obfuscate", methods=["POST"])
def process():
    if not _rate_limit_ok(_client_ip()):
        return jsonify({
            "success": False,
            "error": "Rate limit exceeded. Try again later."
        }), 429

    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Content-Type must be application/json."
        }), 415

    data = request.get_json(silent=True) or {}
    raw_code, validation_error = _validate_source(data.get("code", ""))
    if validation_error:
        return jsonify({"success": False, "error": validation_error}), 400

    settings = data.get("settings", {})
    if not isinstance(settings, dict):
        settings = {}

    token = secrets.token_urlsafe(24)
    created_at = time.time()

    try:
        obfuscated_code = build_enterprise_vm(raw_code, settings)
    except Exception as exc:
        app.logger.exception("Compilation failed")
        return jsonify({
            "success": False,
            "error": f"Compilation failed: {type(exc).__name__}"
        }), 500

    file_path = os.path.join(SAVED_DIR, f"{token}.lua")

    try:
        with CACHE_LOCK:
            SCRIPT_CACHE[token] = {
                "code": obfuscated_code,
                "created_at": created_at,
            }

        # Explicit UTF-8 and restricted permissions where supported.
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(obfuscated_code)

        try:
            os.chmod(file_path, 0o600)
        except OSError:
            pass

    except OSError:
        with CACHE_LOCK:
            SCRIPT_CACHE.pop(token, None)
        return jsonify({
            "success": False,
            "error": "Could not store generated script."
        }), 500

    domain = CUSTOM_DOMAIN.rstrip("/") if CUSTOM_DOMAIN else request.host_url.rstrip("/")
    loader = f'loadstring(game:HttpGet("{domain}/raw/{token}"))()'

    return jsonify({
        "success": True,
        "loader": loader,
        "expires_in": SCRIPT_TTL,
    })


@app.route("/raw/<token>", methods=["GET"])
def serve_script(token):
    # tokens generated by secrets.token_urlsafe() are URL-safe.
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,64}", token):
        return Response("Token Expired or Not Found.", status=404, mimetype="text/plain")

    if request.headers.get("Sec-Fetch-Dest", "") == "document":
        return render_template_string(PROTECTED_HTML_TEMPLATE)

    with CACHE_LOCK:
        entry = SCRIPT_CACHE.get(token)

    code = entry.get("code") if entry else None

    if code is None:
        file_path = os.path.join(SAVED_DIR, f"{token}.lua")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except (OSError, UnicodeError):
            code = None

    if code:
        res = Response(code, mimetype="text/plain")
        res.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        res.headers["Pragma"] = "no-cache"
        res.headers["X-Content-Type-Options"] = "nosniff"
        return res

    return Response(
        "warn('[Classicfuscator] Token Expired or Not Found.')",
        status=404,
        mimetype="text/plain",
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        threaded=True,
    )
