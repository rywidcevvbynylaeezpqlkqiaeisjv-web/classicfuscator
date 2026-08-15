import math
import os
import random
import re
import sqlite3
import string
import time
import uuid
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Persistent Storage Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(BASE_DIR, "saved_scripts")
DB_PATH = os.path.join(BASE_DIR, "database.db")
os.makedirs(SAVED_DIR, exist_ok=True)

SCRIPT_CACHE = {}


def init_db():
    """Initializes SQLite database to persist tokens across server restarts."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS scripts 
           (token TEXT PRIMARY KEY, code TEXT, created_at REAL)"""
    )
    conn.commit()
    conn.close()


init_db()


def random_id(prefix=""):
    """Generates homoglyph-style confusing variable names."""
    chars = ["I", "l", "1", "_"]
    body = "".join(random.choices(chars, k=random.randint(18, 28)))
    return f"{prefix}_{body}"


def ror(val, count, bits=8):
    """Rotate Right for 8-bit integer."""
    return ((val >> count) | (val << (bits - count))) & 0xFF


def virtualize_constants_and_tokens(code: str):
    """
    Tier-1 Obfuscation Engine: Lexically extracts all string literals into an 
    encrypted Constant Pool Table (_K[]), completely eliminating plaintext string constants.
    """
    constants = []

    def add_const(val):
        if val in constants:
            return constants.index(val)
        constants.append(val)
        return len(constants) - 1

    def double_quote_sub(m):
        s = m.group(1)
        if not s or len(s) > 150 or "\n" in s:
            return m.group(0)
        c_idx = add_const(s)
        return f"_K[{c_idx + 1}]"

    def single_quote_sub(m):
        s = m.group(1)
        if not s or len(s) > 150 or "\n" in s:
            return m.group(0)
        c_idx = add_const(s)
        return f"_K[{c_idx + 1}]"

    dq_pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)"'
    sq_pattern = r"'([^'\\]*(?:\\.[^'\\]*)*)'"

    try:
        processed = re.sub(dq_pattern, double_quote_sub, code)
        processed = re.sub(sq_pattern, single_quote_sub, processed)
        return processed, constants
    except Exception:
        return code, []


def obfuscate_lua(code: str, token: str) -> str:
    if not code.strip():
        return "-- Error: Empty script provided."

    # 1. Constant Pool Virtualization Engine
    processed_code, constants = virtualize_constants_and_tokens(code)
    raw_bytes = list(processed_code.encode("utf-8"))

    # 2. Encrypt Constants Pool
    k_seed = random.randint(100000, 999999)
    k_mult = random.randint(5, 29) * 2 + 1
    k_inc = random.randint(1, 255)
    k_shift = random.randint(1, 7)
    k_mask = random.randint(16, 240)

    enc_constants = []
    for c_idx, const_str in enumerate(constants):
        c_bytes = list(const_str.encode("utf-8"))
        enc_c = []
        c_key = (k_seed + c_idx * 17) % 256
        for b_idx, b in enumerate(c_bytes):
            c_key = (c_key * k_mult + k_inc + b_idx) % 256
            enc_c.append((ror(b, k_shift) ^ c_key ^ k_mask ^ ((b_idx * 7 + 11) % 256)) % 256)
        enc_constants.append(enc_c)

    # 3. Encrypt Raw Code Byte Stream
    encrypted_bytes = []
    c_key = k_seed
    for idx, byte in enumerate(raw_bytes):
        c_key = (c_key * k_mult + k_inc + idx * 13) % 256
        rotated = ror(byte, k_shift)
        pos_key = (idx * 7 + 13) % 256
        enc = (rotated ^ c_key ^ k_mask ^ pos_key) % 256
        encrypted_bytes.append(enc)

    # 4. Control Flow Flattening & State Machine Dispatcher
    chunk_size = random.randint(14, 28)
    chunks = [
        encrypted_bytes[i : i + chunk_size]
        for i in range(0, len(encrypted_bytes), chunk_size)
    ]

    chunk_states = list(range(100, 100 + len(chunks)))
    state_map = {}
    for idx, state_id in enumerate(chunk_states):
        next_state = chunk_states[idx + 1] if idx + 1 < len(chunk_states) else 0
        state_map[state_id] = (chunks[idx], next_state)

    # Convert to Lua Tables
    consts_lua = "{" + ",".join("{" + ",".join(map(str, c)) + "}" for c in enc_constants) + "}"
    chunks_lua = "{" + ",".join(f"[{s}]={'{' + ','.join(map(str, c[0])) + '}'}" for s, c in state_map.items()) + "}"
    trans_lua = "{" + ",".join(f"[{s}]={c[1]}" for s, c in state_map.items()) + "}"
    start_state = chunk_states[0]

    # 5. Randomized Homoglyph Identifiers
    v_env = random_id("Env")
    v_loader = random_id("Ld")
    v_char = random_id("Chr")
    v_concat = random_id("Cat")
    v_bxor = random_id("Bx")
    v_rol = random_id("Rl")
    v_kpool = random_id("K")
    v_enc_k = random_id("EK")
    v_chunks = random_id("Data")
    v_trans = random_id("Tr")
    v_state = random_id("St")
    v_out = random_id("Out")
    v_idx = random_id("Idx")
    v_seed = random_id("Sd")
    v_mult = random_id("M")
    v_inc = random_id("C")
    v_shift = random_id("Sh")
    v_mask = random_id("Mk")
    v_clean = random_id("Cln")
    v_res = random_id("Res")
    v_err = random_id("Err")
    v_t0 = random_id("T0")

    # 6. Hardened Tier-1 Custom VM Stub
    lua_stub = f"""--[[ Classicfuscator v9 Enterprise Commercial VM ]]--
return (function(...)
    local {v_env} = (getgenv and getgenv()) or _ENV or _G
    local {v_loader} = {v_env}.loadstring or load

    if type({v_loader}) ~= "function" then
        return
    end

    local {v_char} = string.char
    local {v_concat} = table.concat

    -- Self-Destructing Multi-Vector Anti-Hook Guard
    local {v_clean} = (function()
        local _pcall = pcall
        local _getfenv = getfenv
        local _debug_info = (debug and debug.info)
        local _islclosure = islclosure
        local _isfunctionhooked = isfunctionhooked

        if _isfunctionhooked and _isfunctionhooked({v_loader}) then return false end
        if _islclosure and _islclosure({v_loader}) then return false end
        if _debug_info then
            local src = _debug_info({v_loader}, "s")
            if src and src ~= "[C]" and src ~= "=[C]" then return false end
        end

        if _getfenv and _pcall then
            local local_env = _getfenv(1)
            for lvl = 0, 12 do
                local ok, env = _pcall(_getfenv, lvl)
                if ok and env and env ~= local_env then
                    for k in pairs(env) do
                        if k == "hookfunction" or k == "hookmetamethod" or k == "replaceclosure" then
                            return false
                        end
                    end
                end
            end
        end
        return true
    end)()

    if not {v_clean} then
        return (function() end)() -- Quietly trap execution if hooked
    end
    {v_clean} = nil

    -- Safe Bitwise XOR Engine
    local function {v_bxor}(a, b)
        if bit32 and bit32.bxor then return bit32.bxor(a, b) end
        if bit and bit.bxor then return bit.bxor(a, b) end
        local p, r = 1, 0
        while a > 0 or b > 0 do
            local ra, rb = a % 2, b % 2
            if ra ~= rb then r = r + p end
            a, b, p = math.floor(a / 2), math.floor(b / 2), p * 2
        end
        return r
    end

    local function {v_rol}(val, amt)
        amt = amt % 8
        local l = (val * (2 ^ amt)) % 256
        local r = math.floor(val / (2 ^ (8 - amt)))
        return (l + r) % 256
    end

    -- Cryptographic VM Seed Keys
    local {v_seed} = {k_seed}
    local {v_mult} = {k_mult}
    local {v_inc} = {k_inc}
    local {v_shift} = {k_shift}
    local {v_mask} = {k_mask}

    -- Decrypt Constant Pool (_K Table Virtualization)
    local {v_enc_k} = {consts_lua}
    local _K = {{}}
    for c_idx = 1, #{v_enc_k} do
        local raw_c = {v_enc_k}[c_idx]
        local c_out = {{}}
        local c_key = ({v_seed} + (c_idx - 1) * 17) % 256
        for b_idx = 1, #raw_c do
            c_key = (c_key * {v_mult} + {v_inc} + (b_idx - 1)) % 256
            local pos_key = ((b_idx - 1) * 7 + 11) % 256
            local step1 = {v_bxor}(raw_c[b_idx], pos_key)
            local step2 = {v_bxor}(step1, {v_mask})
            local step3 = {v_bxor}(step2, c_key)
            c_out[#c_out + 1] = {v_char}({v_rol}(step3, {v_shift}))
        end
        _K[c_idx] = {v_concat}(c_out)
    end
    {v_enc_k} = nil

    -- Control-Flow Flattened Execution Loop
    local {v_chunks} = {chunks_lua}
    local {v_trans} = {trans_lua}
    local {v_state} = {start_state}
    local {v_out} = {{}}
    local {v_idx} = 0
    local {v_t0} = (os and os.clock and os.clock()) or 0

    while {v_state} ~= 0 do
        if os and os.clock and (os.clock() - {v_t0} > 10.0) then
            return -- Abort if thread paused by debugger
        end

        local chunk = {v_chunks}[{v_state}]
        if not chunk then break end

        for b_idx = 1, #chunk do
            {v_seed} = ({v_seed} * {v_mult} + {v_inc} + {v_idx} * 13) % 256
            local raw = chunk[b_idx]
            local pos_key = ({v_idx} * 7 + 13) % 256

            local step1 = {v_bxor}(raw, pos_key)
            local step2 = {v_bxor}(step1, {v_mask})
            local step3 = {v_bxor}(step2, {v_seed})
            local unrotated = {v_rol}(step3, {v_shift})

            {v_out}[#{v_out} + 1] = {v_char}(unrotated)
            {v_idx} = {v_idx} + 1
        end

        {v_state} = {v_trans}[{v_state}] or 0
    end

    local payload_str = {v_concat}({v_out})
    {v_out} = nil
    {v_chunks} = nil
    {v_trans} = nil

    local {v_res}, {v_err} = {v_loader}(payload_str, "=[ClassicfuscatorVM]")
    payload_str = nil

    if type({v_res}) == "function" then
        return {v_res}(...)
    else
        error("[Classicfuscator] Syntax Error in Payload: " .. tostring({v_err}), 0)
    end
end)(...)"""

    return lua_stub.strip()


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { 
            background-color: #f2f4f8; 
            color: #1e293b; 
            margin: 0; 
            padding: 40px 20px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
        }
        .card { 
            background: #ffffff; 
            border-radius: 20px; 
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03); 
            width: 100%; 
            max-width: 520px; 
            padding: 36px 32px; 
            border: 1px solid #eef0f4; 
        }
        h1 { 
            font-size: 28px; 
            font-weight: 700; 
            color: #1a1a1a; 
            margin: 0 0 24px 0; 
            letter-spacing: -0.3px;
        }
        .file-upload-box {
            border: 2px dashed #0070f3;
            border-radius: 12px;
            padding: 24px 20px;
            background-color: #ffffff;
            margin-bottom: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .file-upload-box:hover, .file-upload-box.drag-over {
            background-color: #f0f7ff;
            border-color: #0052cc;
        }
        .file-upload-title {
            font-size: 16px;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 6px;
            display: block;
        }
        .file-upload-subtext {
            font-size: 13px;
            color: #64748b;
            margin: 0;
        }
        .or-text {
            font-size: 15px;
            font-weight: 400;
            color: #1e293b;
            margin-bottom: 12px;
        }
        textarea { 
            width: 100%; 
            height: 180px;
            border: 1px solid #dcdfe6; 
            border-radius: 12px; 
            padding: 14px; 
            font-size: 14px; 
            font-family: monospace;
            outline: none; 
            background-color: #ffffff; 
            color: #1e293b; 
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
            resize: vertical;
        }
        textarea:focus { 
            border-color: #0070f3; 
            box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.12);
        }
        .btn { 
            width: 100%; 
            padding: 14px; 
            background-color: #0070f3; 
            color: #ffffff; 
            border: none; 
            border-radius: 12px; 
            font-size: 16px; 
            font-weight: 600; 
            cursor: pointer; 
            margin-top: 20px; 
            transition: background-color 0.2s ease;
            box-shadow: 0 4px 12px rgba(0, 112, 243, 0.2);
        }
        .btn:hover { 
            background-color: #005bb5; 
        }
        .output-container { margin-top: 24px; display: none; }
        .loader-box { 
            background: #f8fafc; 
            border: 1px solid #e2e8f0; 
            border-radius: 12px; 
            padding: 16px; 
        }
        .section-label {
            font-size: 14px;
            font-weight: 600;
            color: #0070f3;
            margin-bottom: 8px;
            display: block;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator</h1>

        <div class="file-upload-box" id="dropZone" onclick="document.getElementById('luaFileInput').click()">
            <span class="file-upload-title">Upload a Lua File:</span>
            <p class="file-upload-subtext" id="dropSubtext">Click to choose or drag & drop file here (.lua, .txt)</p>
            <input type="file" id="luaFileInput" accept=".lua,.luau,.txt" onchange="handleFileSelect(event)" style="display: none;">
        </div>

        <div class="or-text">Or paste your Roblox Lua code here:</div>

        <textarea id="input" placeholder=""></textarea>

        <button class="btn" onclick="obfuscate()">Start Obfuscation</button>

        <div class="output-container" id="outputWrapper">
            <div class="loader-box">
                <span class="section-label">Roblox Loader Script:</span>
                <textarea id="loaderOutput" style="height: 75px; background: #ffffff;" readonly></textarea>
                <button class="btn" style="background-color: #334155; color: #ffffff; box-shadow: none; margin-top: 10px;" onclick="copyLoader()">Copy Loader</button>
            </div>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('dropZone');

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('drag-over');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files.length > 0) {
                readFileContent(files[0]);
            }
        });

        function handleFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) {
                readFileContent(files[0]);
            }
        }

        function readFileContent(file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('input').value = e.target.result;
                document.getElementById('dropSubtext').innerText = "Loaded: " + file.name;
            };
            reader.readAsText(file);
        }

        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const loaderArea = document.getElementById('loaderOutput');
            
            outputWrapper.style.display = "block";
            loaderArea.value = "-- Compiling Commercial Enterprise VM...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                loaderArea.value = data.loader || "-- Error generating loader.";
            } catch (err) {
                loaderArea.value = "-- Generation failed: " + err;
            }
        }

        function copyLoader() {
            const loaderArea = document.getElementById('loaderOutput');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            alert('Loader copied to clipboard!');
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
        body { 
            background-color: #f2f4f8; 
            color: #1e293b; 
            margin: 0; 
            padding: 20px; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
        }
        .card { 
            background: #ffffff; 
            border-radius: 20px; 
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); 
            width: 100%; 
            max-width: 440px; 
            padding: 40px 28px; 
            border: 1px solid #eef0f4; 
            text-align: center;
        }
        h1 { 
            font-size: 24px; 
            font-weight: 700; 
            color: #1a1a1a; 
            margin: 0 0 10px 0; 
            letter-spacing: -0.3px;
        }
        p { 
            font-size: 15px; 
            color: #64748b; 
            margin: 0; 
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>Protected By Classicfuscator</h1>
        <p>Cannot be Shown Publicy</p>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/obfuscate", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code", "")
    
    # Generate dynamic 32-character Hex Token
    token = uuid.uuid4().hex
    
    # Compile with Constant Virtualization + State Machine VM
    obfuscated_code = obfuscate_lua(raw_code, token)
    
    # Store in RAM Cache
    SCRIPT_CACHE[token] = {
        "code": obfuscated_code,
        "created_at": time.time(),
        "active": True
    }
    
    # Store in Disk File
    file_path = os.path.join(SAVED_DIR, f"{token}.lua")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_code)

    # Store in Persistent SQLite Database
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO scripts (token, code, created_at) VALUES (?, ?, ?)",
            (token, obfuscated_code, time.time()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Save Error:", e)
    
    # Enforce HTTPS URL
    domain_url = request.host_url.rstrip("/")
    if domain_url.startswith("http://") and not ("127.0.0.1" in domain_url or "localhost" in domain_url):
        domain_url = domain_url.replace("http://", "https://", 1)

    loader_script = f'loadstring(game:HttpGet("{domain_url}/raw/{token}"))()'

    return jsonify({
        "loader": loader_script,
        "token": token
    })


@app.route("/verify/<token>", methods=["POST"])
def verify_session(token):
    """Server-side authorization endpoint."""
    if token in SCRIPT_CACHE and SCRIPT_CACHE[token].get("active"):
        return jsonify({"valid": True})
    return jsonify({"valid": False}), 403


@app.route("/raw/<token>", methods=["GET"])
def serve_script(token):
    """
    Serves raw payload to Roblox client, while serving a styled card to web browsers.
    """
    user_agent = request.headers.get("User-Agent", "").lower()

    # Browser Detection (Chrome, Safari, Firefox, Edge, Opera)
    is_browser = any(b in user_agent for b in ["mozilla", "chrome", "safari", "firefox", "edge", "opera"])
    is_roblox_client = any(r in user_agent for r in ["roblox", "android", "iphone", "ipad"]) or not is_browser

    # If opened directly in a standard web browser, render the styled card page
    if is_browser and "roblox" not in user_agent:
        return render_template_string(PROTECTED_HTML_TEMPLATE)

    # Roblox Client / Executor Retrieval
    code = None

    # Check RAM Cache
    if token in SCRIPT_CACHE:
        code = SCRIPT_CACHE[token]["code"]

    # Check Persistent SQLite Database
    if not code:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT code FROM scripts WHERE token = ?", (token,))
            row = c.fetchone()
            if row:
                code = row[0]
                SCRIPT_CACHE[token] = {"code": code, "created_at": time.time(), "active": True}
            conn.close()
        except Exception as e:
            print("DB Read Error:", e)

    # Check Disk Storage
    if not code:
        file_path = os.path.join(SAVED_DIR, f"{token}.lua")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

    # If code found, return HTTP 200 plain text payload
    if code:
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        res.headers["Pragma"] = "no-cache"
        return res

    # Graceful Fallback: Return HTTP 200 Lua Comment so Roblox doesn't crash with 404
    return Response("-- Error: Invalid or Expired Token. Please generate a new loader from Classicfuscator.", status=200, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
