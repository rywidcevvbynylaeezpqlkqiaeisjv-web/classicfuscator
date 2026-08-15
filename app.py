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
    body = "".join(random.choices(chars, k=random.randint(16, 24)))
    return f"{prefix}_{body}"


# ==============================================================================
# 1. AST-LEVEL LEXER & TOKEN TRANSFORMER
# ==============================================================================

LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while"
}

# Regex Tokenizer for Lua
TOKEN_SPEC = [
    ("COMMENT_LONG", r"--\[(=*)\[[\s\S]*?\]\1\]"),
    ("COMMENT_SHORT", r"--[^\n]*"),
    ("STRING_LONG", r"\[(=*)\[[\s\S]*?\]\1\]"),
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
    """Mutates numeric constants into randomized arithmetic/bitwise expressions."""
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
            # Addition / Subtraction splitting
            offset = random.randint(10, 500)
            return f"(({val + offset}) - {offset})"
        elif mode == 2:
            # Multiplication / Subtraction
            mult = random.randint(2, 6)
            base = val * mult
            return f"(({base} / {mult}))"
        else:
            # XOR formula
            xor_key = random.randint(1, 255)
            xor_res = val ^ xor_key
            return f"((bit32 and bit32.bxor({xor_res}, {xor_key})) or ({val}))"
    except Exception:
        return num_str


def transform_string(str_val: str, dec_func_name: str) -> str:
    """Encrypts string literals and replaces them with dynamic decryptor calls."""
    # Strip enclosing quotes
    if (str_val.startswith('"') and str_val.endswith('"')) or (str_val.startswith("'") and str_val.endswith("'")):
        inner = str_val[1:-1]
        try:
            # Process escape sequences
            inner = bytes(inner, "utf-8").decode("unicode_escape")
        except Exception:
            pass
    elif str_val.startswith("["):
        # Long brackets [[ ... ]]
        inner = re.sub(r"^\[=*\[|\]=*\]$", "", str_val)
    else:
        inner = str_val

    raw_bytes = list(inner.encode("utf-8"))
    key = random.randint(1, 255)
    enc_bytes = [(b ^ key) for b in raw_bytes]
    bytes_table = "{" + ",".join(map(str, enc_bytes)) + "}"
    return f"{dec_func_name}({bytes_table}, {key})"


def ast_obfuscate(lua_code: str, dec_func_name: str) -> str:
    """Pre-processes raw Lua, encrypting all strings, mutating numbers, and stripping comments."""
    output_tokens = []
    
    for match in TOKEN_REGEX.finditer(lua_code):
        kind = match.lastgroup
        val = match.group()

        if kind in ("COMMENT_LONG", "COMMENT_SHORT"):
            output_tokens.append(" ")
            continue
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

def ror(val, count, bits=8):
    return ((val >> count) | (val << (bits - count))) & 0xFF


def obfuscate_lua(code: str, token: str) -> str:
    if not code.strip():
        return "print('[Classicfuscator] Empty script executed.')"

    v_dec = random_id("Dec")
    
    # Stage 1: AST Token Transformation & String Virtualization
    ast_transformed_code = ast_obfuscate(code, v_dec)

    # Stage 2: Binary Bytecode Stream Encryption
    raw_bytes = list(ast_transformed_code.encode("utf-8"))
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

    chunks_lua = "{" + ",".join(f"[{s}]={'{' + ','.join(map(str, c[0])) + '}'}" for s, c in state_map.items()) + "}"
    trans_lua = "{" + ",".join(f"[{s}]={c[1]}" for s, c in state_map.items()) + "}"
    start_state = chunk_states[0] if chunk_states else 0

    # Stage 3: Randomized VM Variables & Identifiers
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
    v_anti = random_id("Anti")
    v_genv = random_id("Genv")

    lua_stub = f"""--[[ Classicfuscator v10.0 Enterprise Hybrid VM ]]--
return (function(...)
    local {v_genv} = (getgenv and getgenv()) or _ENV or _G

    -- Anti-Hook & Integrity Sentinel
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
        warn("[Classicfuscator] Execution environment unsupported.")
        return
    end

    local {v_char} = string.char
    local {v_concat} = table.concat

    -- Safe Hardware/Software Bitwise XOR
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

    -- Embedded AST String Decryptor
    {v_genv}.{v_dec} = function(bytes, k)
        local t = {{}}
        for i = 1, #bytes do
            t[i] = {v_char}({v_bxor}(bytes[i], k))
        end
        return {v_concat}(t)
    end

    -- VM Key States
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

    -- State-Machine Dispatch Loop
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
    else
        warn("[Classicfuscator] Runtime error: " .. tostring({v_err}))
    end
end)(...)"""

    return lua_stub.strip()


# ==============================================================================
# 3. WEB INTERFACE & FLASK API
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator v10.0 Enterprise</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #0f172a; color: #f8fafc; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #1e293b; border-radius: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4); width: 100%; max-width: 580px; padding: 36px 32px; border: 1px solid #334155; }
        h1 { font-size: 26px; font-weight: 700; color: #38bdf8; margin: 0 0 8px 0; }
        .subtitle { font-size: 13px; color: #94a3b8; margin-bottom: 24px; }
        textarea { width: 100%; height: 180px; border: 1px solid #475569; border-radius: 12px; padding: 14px; font-size: 14px; font-family: monospace; outline: none; background-color: #0f172a; color: #38bdf8; resize: vertical; }
        .btn { width: 100%; padding: 14px; background-color: #0284c7; color: #ffffff; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 18px; transition: background-color 0.2s; }
        .btn:hover { background-color: #0369a1; }
        .output-container { margin-top: 24px; display: none; }
        .loader-box { background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 16px; }
        .section-label { font-size: 14px; font-weight: 600; color: #38bdf8; margin-bottom: 8px; display: block; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator v10.0</h1>
        <div class="subtitle">AST-Flattening • String Virtualization • Anti-Dump Protection</div>
        <textarea id="input" placeholder="print('Hello from Protected Script!')"></textarea>
        <button class="btn" onclick="obfuscate()">Obfuscate & Generate Loader</button>

        <div class="output-container" id="outputWrapper">
            <div class="loader-box">
                <span class="section-label">Roblox Loader Script:</span>
                <textarea id="loaderOutput" style="height: 110px;" readonly></textarea>
                <button class="btn" style="background-color: #334155; margin-top: 10px;" onclick="copyLoader()">Copy Loader</button>
            </div>
        </div>
    </div>

    <script>
        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const loaderArea = document.getElementById('loaderOutput');
            
            outputWrapper.style.display = "block";
            loaderArea.value = "-- Compiling AST & VM Pipeline...";

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
    <title>Protected By Classicfuscator</title>
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 40px; border-radius: 16px; text-align: center; border: 1px solid #334155; }
        h1 { color: #38bdf8; font-size: 22px; }
        p { color: #94a3b8; }
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
    
    domain_url = request.host_url.rstrip("/")
    if request.headers.get("X-Forwarded-Proto") == "https" or (domain_url.startswith("http://") and not ("127.0.0.1" in domain_url or "localhost" in domain_url)):
        domain_url = domain_url.replace("http://", "https://", 1)

    loader_script = (
        f'local ok, res = pcall(function() return game:HttpGet("{domain_url}/raw/{token}") end) '
        f'if not ok or not res or #res == 0 then warn("[Loader] Download failed: " .. tostring(res)) return end '
        f'if res:sub(1,1) == "<" then warn("[Loader] Server returned HTML. Verify server URL.") return end '
        f'local fn, err = loadstring(res) '
        f'if not fn then warn("[Loader] Load Error: " .. tostring(err)) return end '
        f'fn()'
    )

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
