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

# Render Custom Domain (auto-detects if left blank)
CUSTOM_DOMAIN = "https://classicfuscator.onrender.com"

# Persistent Storage
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(BASE_DIR, "saved_scripts")
DB_PATH = os.path.join(BASE_DIR, "database.db")
os.makedirs(SAVED_DIR, exist_ok=True)

SCRIPT_CACHE = {}


def init_db():
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
    chars = ["I", "l", "1", "_"]
    body = "".join(random.choices(chars, k=random.randint(18, 26)))
    return f"{prefix}_{body}"


def ror(val, count, bits=8):
    return ((val >> count) | (val << (bits - count))) & 0xFF


# ==============================================================================
# 1. FIXED AST-LEVEL LEXER & CONSTANT TRANSFORMER
# ==============================================================================

TOKEN_SPEC = [
    ("COMMENT_LONG", r"--\[\[[\s\S]*?\]\]|--\[=\[[\s\S]*?\]=\]|--\[==\[[\s\S]*?\]==\]"),
    ("COMMENT_SHORT", r"--[^\n]*"),
    ("STRING_LONG", r"\[\[[\s\S]*?\]\]|\[=\[[\s\S]*?\]=\]|\[==\[[\s\S]*?\]==\]"),
    ("STRING_SQ", r"'([^'\\]|\\.)*'"),
    ("STRING_DQ", r'"([^"\\]|\\.)*"'),
    ("NUMBER_HEX", r"0[xX][0-9a-fA-F]+"),
    ("NUMBER_DEC", r"\b\d+\.?\d*(?:[eE][+-]?\d+)?\b"),
    ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("SYMBOL", r"\.\.\.|\.\.|==|~=|<=|>=|::|[-+*/%^#=<>(){}\[\];:,.]"),
    ("WHITESPACE", r"\s+"),
]
TOKEN_REGEX = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))


def transform_number(num_str: str) -> str:
    try:
        if num_str.lower().startswith("0x"):
            val = int(num_str, 16)
        elif "." in num_str or "e" in num_str.lower():
            return num_str
        else:
            val = int(num_str)

        if val < 0 or val > 65535:
            return num_str

        mode = random.randint(1, 3)
        if mode == 1:
            offset = random.randint(100, 999)
            return f"(({val + offset}) - {offset})"
        elif mode == 2:
            mult = random.randint(2, 6)
            base = val * mult
            return f"(({base} / {mult}))"
        else:
            xor_key = random.randint(1, 255)
            xor_res = val ^ xor_key
            return f"((bit32 and bit32.bxor({xor_res}, {xor_key})) or ({val}))"
    except Exception:
        return num_str


def transform_string(str_val: str, dec_func_name: str) -> str:
    if (str_val.startswith('"') and str_val.endswith('"')) or (str_val.startswith("'") and str_val.endswith("'")):
        inner = str_val[1:-1]
        try:
            inner = bytes(inner, "utf-8").decode("unicode_escape")
        except Exception:
            pass
    elif str_val.startswith("["):
        inner = re.sub(r"^\[=*\[|\]=*\]$", "", str_val)
    else:
        inner = str_val

    raw_bytes = list(inner.encode("utf-8"))
    key = random.randint(1, 255)
    enc_bytes = [(b ^ key) for b in raw_bytes]
    bytes_table = "{" + ",".join(map(str, enc_bytes)) + "}"
    return f"{dec_func_name}({bytes_table}, {key})"


def ast_obfuscate(lua_code: str, dec_func_name: str) -> str:
    output_tokens = []
    for match in TOKEN_REGEX.finditer(lua_code):
        kind = match.lastgroup
        val = match.group()

        if kind in ("COMMENT_LONG", "COMMENT_SHORT"):
            output_tokens.append(" ")
        elif kind in ("STRING_LONG", "STRING_SQ", "STRING_DQ"):
            output_tokens.append(transform_string(val, dec_func_name))
        elif kind in ("NUMBER_HEX", "NUMBER_DEC"):
            output_tokens.append(transform_number(val))
        elif kind == "WHITESPACE":
            output_tokens.append(" ")
        else:
            output_tokens.append(val)

    return "".join(output_tokens)


# ==============================================================================
# 2. RUNTIME VM & HARDENED PAYLOAD COMPILER
# ==============================================================================

def obfuscate_lua(code: str, token: str) -> str:
    if not code.strip():
        return "print('[Classicfuscator] Empty script executed.')"

    v_dec = random_id("Dec")
    ast_transformed = ast_obfuscate(code, v_dec)

    raw_bytes = list(ast_transformed.encode("utf-8"))
    k_seed = random.randint(100000, 999999)
    k_mult = random.randint(5, 29) * 2 + 1
    k_inc = random.randint(1, 255)
    k_shift = random.randint(1, 7)
    k_mask = random.randint(16, 240)

    encrypted_bytes = []
    c_key = k_seed
    for idx, byte in enumerate(raw_bytes):
        c_key = (c_key * k_mult + k_inc + idx * 13) % 256
        rotated = ror(byte, k_shift)
        pos_key = (idx * 7 + 13) % 256
        enc = (rotated ^ c_key ^ k_mask ^ pos_key) % 256
        encrypted_bytes.append(enc)

    chunk_size = random.randint(16, 32)
    chunks = [
        encrypted_bytes[i : i + chunk_size]
        for i in range(0, len(encrypted_bytes), chunk_size)
    ]

    chunk_states = list(range(100, 100 + len(chunks)))
    state_map = {}
    for idx, state_id in enumerate(chunk_states):
        next_state = chunk_states[idx + 1] if idx + 1 < len(chunk_states) else 0
        state_map[state_id] = (chunks[idx], next_state)

    chunks_lua = "{" + ",".join(f"[{s}]={'{' + ','.join(map(str, c[0])) + '}'}" for s, c in state_map.items()) + "}"
    trans_lua = "{" + ",".join(f"[{s}]={c[1]}" for s, c in state_map.items()) + "}"
    start_state = chunk_states[0] if chunk_states else 0

    v_env = random_id("Env")
    v_loader = random_id("Ld")
    v_char = random_id("Chr")
    v_concat = random_id("Cat")
    v_bxor = random_id("Bx")
    v_rol = random_id("Rl")
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
    v_res = random_id("Res")
    v_err = random_id("Err")
    v_genv = random_id("Genv")
    v_anti = random_id("Anti")

    lua_stub = f"""--[[ Protected by Classicfuscator Enterprise ]]--
return (function(...)
    local {v_genv} = (getgenv and getgenv()) or _ENV or _G

    local function {v_anti}()
        if debug and (debug.info or debug.getinfo) then
            local get_i = debug.info or debug.getinfo
            local ok, info = pcall(function() return get_i(1, "slna") end)
            if not ok then return false end
        end
        return true
    end

    if not {v_anti}() then
        while true do end
        return
    end

    local {v_loader} = {v_genv}.loadstring or loadstring or load
    if type({v_loader}) ~= "function" then
        return
    end

    local {v_char} = string.char
    local {v_concat} = table.concat

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

    {v_genv}.{v_dec} = function(bytes, k)
        local t = {{}}
        for i = 1, #bytes do
            t[i] = {v_char}({v_bxor}(bytes[i], k))
        end
        return {v_concat}(t)
    end

    local {v_seed} = {k_seed}
    local {v_mult} = {k_mult}
    local {v_inc} = {k_inc}
    local {v_shift} = {k_shift}
    local {v_mask} = {k_mask}

    local {v_chunks} = {chunks_lua}
    local {v_trans} = {trans_lua}
    local {v_state} = {start_state}
    local {v_out} = {{}}
    local {v_idx} = 0

    while {v_state} ~= 0 do
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

    local {v_res}, {v_err} = {v_loader}(payload_str)
    payload_str = nil

    if type({v_res}) == "function" then
        return {v_res}(...)
    end
end)(...)"""

    return lua_stub.strip()


# ==============================================================================
# 3. WEB DASHBOARD & API
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator Enterprise</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b0f19; color: #f1f5f9; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #111827; border-radius: 16px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6); width: 100%; max-width: 560px; padding: 32px; border: 1px solid #1f2937; }
        h1 { font-size: 24px; font-weight: 700; color: #38bdf8; margin: 0 0 6px 0; letter-spacing: -0.5px; }
        .subtitle { font-size: 13px; color: #94a3b8; margin-bottom: 20px; }
        textarea { width: 100%; height: 160px; border: 1px solid #374151; border-radius: 10px; padding: 14px; font-size: 13px; font-family: monospace; outline: none; background-color: #030712; color: #38bdf8; resize: vertical; }
        textarea:focus { border-color: #0284c7; }
        .btn { width: 100%; padding: 13px; background-color: #0284c7; color: #ffffff; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 16px; }
        .btn:hover { background-color: #0369a1; }
        .output-container { margin-top: 20px; display: none; }
        .loader-box { background: #030712; border: 1px solid #1e293b; border-radius: 10px; padding: 14px; }
        .section-label { font-size: 12px; font-weight: 600; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; display: block; }
        .loader-text { width: 100%; height: 48px; background: #111827; border: 1px solid #374151; border-radius: 8px; color: #38bdf8; font-family: monospace; font-size: 12.5px; padding: 12px; white-space: nowrap; overflow-x: auto; resize: none; }
        .copy-btn { background-color: #1f2937; color: #e2e8f0; border: 1px solid #374151; margin-top: 8px; }
        .copy-btn:hover { background-color: #374151; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator</h1>
        <div class="subtitle">AST-Flattening • String Virtualization • Anti-Dump Protection</div>
        <textarea id="input" placeholder="print('Hello from Protected Script!')"></textarea>
        <button class="btn" id="submitBtn" onclick="obfuscate()">Obfuscate Script</button>

        <div class="output-container" id="outputWrapper">
            <div class="loader-box">
                <span class="section-label">Roblox Loader (1-Liner)</span>
                <textarea id="loaderOutput" class="loader-text" readonly></textarea>
                <button class="btn copy-btn" id="copyBtn" onclick="copyLoader()">Copy Loader</button>
            </div>
        </div>
    </div>

    <script>
        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const loaderArea = document.getElementById('loaderOutput');
            const submitBtn = document.getElementById('submitBtn');
            
            outputWrapper.style.display = "block";
            loaderArea.value = "Compiling AST & VM Pipeline...";
            submitBtn.innerText = "Processing...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });
                const data = await response.json();
                loaderArea.value = data.loader || "-- Generation failed.";
            } catch (err) {
                loaderArea.value = "-- Error connecting to server.";
            } finally {
                submitBtn.innerText = "Obfuscate Script";
            }
        }

        function copyLoader() {
            const loaderArea = document.getElementById('loaderOutput');
            const copyBtn = document.getElementById('copyBtn');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            copyBtn.innerText = "Copied to Clipboard!";
            setTimeout(() => { copyBtn.innerText = "Copy Loader"; }, 2000);
        }
    </script>
</body>
</html>
"""

PROTECTED_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Protected Script</title>
    <style>
        body { background-color: #0b0f19; color: #f1f5f9; font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: #111827; padding: 40px; border-radius: 16px; text-align: center; border: 1px solid #374151; }
        h1 { color: #38bdf8; font-size: 20px; margin-bottom: 8px; }
        p { color: #94a3b8; font-size: 14px; margin: 0; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Protected Script</h1>
        <p>This payload is protected and can only be executed via Roblox.</p>
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
    
    token = uuid.uuid4().hex
    obfuscated_code = obfuscate_lua(raw_code, token)
    
    SCRIPT_CACHE[token] = {
        "code": obfuscated_code,
        "created_at": time.time(),
        "active": True
    }
    
    file_path = os.path.join(SAVED_DIR, f"{token}.lua")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_code)

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
    
    if CUSTOM_DOMAIN:
        domain_url = CUSTOM_DOMAIN.rstrip("/")
    else:
        domain_url = request.host_url.rstrip("/")
        if request.headers.get("X-Forwarded-Proto") == "https" or (domain_url.startswith("http://") and not ("127.0.0.1" in domain_url or "localhost" in domain_url)):
            domain_url = domain_url.replace("http://", "https://", 1)

    # 1-Liner Output
    loader_script = f'loadstring(game:HttpGet("{domain_url}/raw/{token}"))()'

    return jsonify({
        "loader": loader_script,
        "token": token
    })


@app.route("/raw/<token>", methods=["GET"])
def serve_script(token):
    sec_fetch_dest = request.headers.get("Sec-Fetch-Dest", "").lower()
    sec_ch_ua = request.headers.get("Sec-Ch-Ua")

    is_human_browser = (sec_fetch_dest == "document" and bool(sec_ch_ua))
    if is_human_browser:
        return render_template_string(PROTECTED_HTML_TEMPLATE)

    code = None

    if token in SCRIPT_CACHE:
        code = SCRIPT_CACHE[token]["code"]

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

    if not code:
        file_path = os.path.join(SAVED_DIR, f"{token}.lua")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

    if code:
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return res

    return Response("warn('[Classicfuscator] Script token expired or not found.')", status=200, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
