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

# Render Custom Domain Configuration
CUSTOM_DOMAIN = "https://classicfuscator.onrender.com"

# Persistent Storage Paths
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
    body = "".join(random.choices(chars, k=random.randint(20, 28)))
    return f"{prefix}_{body}"


def ror(val, count, bits=8):
    """Rotate Right for 8-bit integer."""
    return ((val >> count) | (val << (bits - count))) & 0xFF


# ==============================================================================
# 1. LUA SYNTAX VALIDATION & TOKEN PARSER
# ==============================================================================

LUA_KEYWORDS = {
    "and", "break", "do", "else", "elseif", "end", "false", "for",
    "function", "if", "in", "local", "nil", "not", "or", "repeat",
    "return", "then", "true", "until", "while"
}

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


def validate_lua_syntax(lua_code: str) -> tuple[bool, str]:
    """
    Validates Lua syntax:
    - Empty or whitespace input
    - Unclosed strings & long brackets
    - Unmatched parentheses, square brackets, and curly braces
    - Mismatched or unclosed block keywords (function, if, do, while, repeat, end, until)
    """
    if not lua_code or not lua_code.strip():
        return False, "Input code is empty."

    bracket_stack = []
    block_stack = []
    tokens = []
    pos = 0

    for match in TOKEN_REGEX.finditer(lua_code):
        start, end = match.span()
        if start > pos:
            unparsed = lua_code[pos:start].strip()
            if unparsed:
                return False, f"Unexpected token or unclosed literal near '{unparsed}'"
        pos = end

        kind = match.lastgroup
        val = match.group()
        if kind != "WHITESPACE" and not kind.startswith("COMMENT"):
            tokens.append((kind, val))

    if pos < len(lua_code):
        unparsed = lua_code[pos:].strip()
        if unparsed:
            return False, f"Unclosed string, comment, or invalid token near '{unparsed}'"

    # Syntax block & bracket verification
    for kind, val in tokens:
        if val in ("(", "[", "{"):
            bracket_stack.append(val)
        elif val in (")", "]", "}"):
            if not bracket_stack:
                return False, f"Unmatched closing bracket '{val}'"
            last_b = bracket_stack.pop()
            expected = {")": "(", "]": "[", "}": "{"}[val]
            if last_b != expected:
                return False, f"Mismatched bracket: expected closing for '{last_b}', got '{val}'"

        if kind == "IDENTIFIER":
            if val == "function":
                block_stack.append("function")
            elif val == "do":
                block_stack.append("do")
            elif val == "then":
                block_stack.append("if")
            elif val == "repeat":
                block_stack.append("repeat")
            elif val in ("elseif", "else"):
                if not block_stack or block_stack[-1] != "if":
                    return False, f"Unexpected '{val}' without matching 'if/then' condition"
            elif val == "end":
                if not block_stack:
                    return False, "Unexpected 'end' with no opening block"
                popped = block_stack.pop()
                if popped not in ("function", "do", "if"):
                    return False, f"Mismatched 'end' for '{popped}' block"
            elif val == "until":
                if not block_stack or block_stack[-1] != "repeat":
                    return False, "Unexpected 'until' with no matching 'repeat' loop"
                block_stack.pop()

    if bracket_stack:
        return False, f"Unclosed bracket '{bracket_stack[-1]}'"

    if block_stack:
        return False, f"Missing 'end' or 'until' for unclosed '{block_stack[-1]}' block"

    return True, ""


# ==============================================================================
# 2. S-TIER AST MUTATOR & CONSTANT TRANSFORMER
# ==============================================================================

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

        mode = random.randint(1, 4)
        if mode == 1:
            offset = random.randint(150, 850)
            return f"(({val + offset}) - {offset})"
        elif mode == 2:
            mult = random.randint(2, 8)
            base = val * mult
            return f"(({base} / {mult}))"
        elif mode == 3:
            xor_key = random.randint(1, 255)
            xor_res = val ^ xor_key
            return f"((bit32 and bit32.bxor({xor_res}, {xor_key})) or ({val}))"
        else:
            p1 = random.randint(10, 100)
            p2 = val + p1 * 2
            return f"(({p2} - ({p1} * 2)))"
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
    mask = random.randint(1, 255)
    
    enc_bytes = []
    for idx, b in enumerate(raw_bytes):
        pos_k = (key + (idx * 7) + 11) % 256
        enc_bytes.append((b ^ pos_k ^ mask) % 256)
        
    bytes_table = "{" + ",".join(map(str, enc_bytes)) + "}"
    return f"{dec_func_name}({bytes_table}, {key}, {mask})"


def ast_obfuscate(lua_code: str, dec_func_name: str) -> str:
    tokens = []
    for match in TOKEN_REGEX.finditer(lua_code):
        kind = match.lastgroup
        val = match.group()
        tokens.append((kind, val))

    renamed_map = {}
    for i, (kind, val) in enumerate(tokens):
        if kind == "IDENTIFIER" and val in ("local", "function", "for"):
            j = i + 1
            while j < len(tokens) and tokens[j][0] == "WHITESPACE":
                j += 1
            if j < len(tokens) and tokens[j][0] == "IDENTIFIER" and tokens[j][1] not in LUA_KEYWORDS:
                var_name = tokens[j][1]
                if var_name not in renamed_map and len(var_name) > 1:
                    renamed_map[var_name] = random_id("v")

    output = []
    for i, (kind, val) in enumerate(tokens):
        if kind in ("COMMENT_LONG", "COMMENT_SHORT"):
            output.append(" ")
        elif kind in ("STRING_LONG", "STRING_SQ", "STRING_DQ"):
            output.append(transform_string(val, dec_func_name))
        elif kind in ("NUMBER_HEX", "NUMBER_DEC"):
            output.append(transform_number(val))
        elif kind == "IDENTIFIER":
            if val == "true":
                k1 = random.randint(10, 99)
                output.append(f"({k1} == {k1})")
            elif val == "false":
                k1 = random.randint(10, 99)
                output.append(f"({k1} == {k1 + 1})")
            elif val == "nil":
                output.append("({[0]=nil}[1])")
            elif val in renamed_map:
                prev_non_ws = None
                for k in range(i - 1, -1, -1):
                    if tokens[k][0] != "WHITESPACE":
                        prev_non_ws = tokens[k]
                        break
                if prev_non_ws and prev_non_ws[1] in (".", ":"):
                    output.append(val)
                else:
                    output.append(renamed_map[val])
            else:
                output.append(val)
        elif kind == "WHITESPACE":
            output.append(" ")
        else:
            output.append(val)

    return "".join(output)


# ==============================================================================
# 3. RUNTIME VM, SENTINEL MATRIX & POISONING ENGINE
# ==============================================================================

def obfuscate_lua(code: str, token: str) -> str:
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

    lua_stub = f"""--[[ Classicfuscator Enterprise Sentinel VM ]]--
return (function(...)
    local {v_genv} = (getgenv and getgenv()) or _ENV or _G

    local function {v_anti}()
        if debug and (debug.info or debug.getinfo) then
            local get_i = debug.info or debug.getinfo
            local ok, info = pcall(function() return get_i(1, "slna") end)
            if not ok then return false end
        end

        local ts = tostring
        if ts(pcall):find("hook") or ts(ts):find("hook") or ts(type):find("hook") or ts(setmetatable):find("hook") then
            return false
        end

        if getrawmetatable then
            local mt = getrawmetatable({v_genv})
            if mt and (rawget(mt, "__index") or rawget(mt, "__namecall")) then
                local idx = rawget(mt, "__index")
                if type(idx) == "function" and ts(idx):find("hook") then
                    return false
                end
            end
        end

        return true
    end

    local {v_seed} = {k_seed}
    if not {v_anti}() then
        {v_seed} = ({v_seed} ^ 0xDEADBEEF) % 256
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

    {v_genv}.{v_dec} = function(bytes, k, m)
        local t = {{}}
        for i = 1, #bytes do
            local pos_k = (k + ((i - 1) * 7) + 11) % 256
            local step1 = {v_bxor}(bytes[i], m)
            t[i] = {v_char}({v_bxor}(step1, pos_k))
        end
        return {v_concat}(t)
    end

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
# 4. LIGHT THEME DASHBOARD & FLASK API
# ==============================================================================

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
        .loader-text {
            width: 100%;
            height: 48px;
            background: #ffffff;
            border: 1px solid #dcdfe6;
            border-radius: 8px;
            color: #1e293b;
            font-family: monospace;
            font-size: 13px;
            padding: 12px;
            white-space: nowrap;
            overflow-x: auto;
            resize: none;
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

        <button class="btn" id="submitBtn" onclick="obfuscate()">Start Obfuscation</button>

        <div class="output-container" id="outputWrapper">
            <div class="loader-box">
                <span class="section-label">Roblox Loader Script:</span>
                <textarea id="loaderOutput" class="loader-text" readonly></textarea>
                <button class="btn" id="copyBtn" style="background-color: #334155; color: #ffffff; box-shadow: none; margin-top: 10px;" onclick="copyLoader()">Copy Loader</button>
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
            const submitBtn = document.getElementById('submitBtn');
            
            if (!inputCode.trim()) {
                outputWrapper.style.display = "block";
                loaderArea.value = "-- Error: Input script is empty. Please enter your Lua code.";
                return;
            }

            outputWrapper.style.display = "block";
            loaderArea.value = "-- Validating syntax & compiling S-Tier pipeline...";
            submitBtn.innerText = "Processing...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                if (response.ok && data.loader) {
                    loaderArea.value = data.loader;
                } else {
                    loaderArea.value = "-- " + (data.error || "Syntax error detected. Obfuscation aborted.");
                }
            } catch (err) {
                loaderArea.value = "-- Network error: Could not connect to server.";
            } finally {
                submitBtn.innerText = "Start Obfuscation";
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
        <p>Cannot be shown publicly.</p>
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
    
    # 1. Validation: Disallow empty input
    if not raw_code or not raw_code.strip():
        return jsonify({
            "success": False,
            "error": "Error: Input script cannot be empty."
        }), 400

    # 2. Validation: Syntax Error Check
    is_valid, error_message = validate_lua_syntax(raw_code)
    if not is_valid:
        return jsonify({
            "success": False,
            "error": f"Syntax Error: {error_message}"
        }), 400
    
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

    # Clean 1-Liner Output
    loader_script = f'loadstring(game:HttpGet("{domain_url}/raw/{token}"))()'

    return jsonify({
        "success": True,
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
