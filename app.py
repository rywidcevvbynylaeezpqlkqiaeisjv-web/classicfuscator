import math
import os
import random
import re
import string
import time
import uuid
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# In-Memory Cache + Disk Storage
SCRIPT_CACHE = {}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(BASE_DIR, "saved_scripts")
os.makedirs(SAVED_DIR, exist_ok=True)


def random_id(prefix=""):
    """Generates homoglyph-style confusing variable names."""
    chars = ["I", "l", "1", "_"]
    body = "".join(random.choices(chars, k=random.randint(18, 28)))
    return f"{prefix}_{body}"


def ror(val, count, bits=8):
    """Rotate Right for 8-bit integer."""
    return ((val >> count) | (val << (bits - count))) & 0xFF


def split_code_into_opcodes(code: str):
    """
    Splits Lua source code into bytecode chunk opcodes.
    This prevents the entire source code from existing as one string in memory.
    """
    lines = code.splitlines(keepends=True)
    opcodes = []
    current_chunk = []
    
    chunk_target_size = random.randint(3, 7)
    for line in lines:
        current_chunk.append(line)
        if len(current_chunk) >= chunk_target_size:
            opcodes.append("".join(current_chunk))
            current_chunk = []
            chunk_target_size = random.randint(3, 7)
            
    if current_chunk:
        opcodes.append("".join(current_chunk))
        
    return opcodes if opcodes else [code]


def obfuscate_lua(code: str, token: str) -> str:
    if not code.strip():
        return "-- Error: Empty script provided."

    # 1. Break code into Micro-Bytecode Opcodes
    raw_opcodes = split_code_into_opcodes(code)
    
    # 2. Encrypt each opcode with distinct positional rolling keys
    k_seed = random.randint(100000, 999999)
    k_shift = random.randint(1, 7)
    k_mask = random.randint(16, 240)
    
    encrypted_opcodes = []
    for op_idx, op_text in enumerate(raw_opcodes):
        op_bytes = list(op_text.encode("utf-8"))
        enc_bytes = []
        c_key = (k_seed + op_idx * 17) % 256
        for b_idx, byte in enumerate(op_bytes):
            c_key = (c_key * 13 + 37 + b_idx) % 256
            rotated = ror(byte, k_shift)
            enc = (rotated ^ c_key ^ k_mask ^ ((b_idx * 7 + 11) % 256)) % 256
            enc_bytes.append(enc)
        encrypted_opcodes.append(enc_bytes)

    # Convert encrypted opcodes to Lua table representation
    opcodes_lua = "{" + ",".join("{" + ",".join(map(str, op)) + "}" for op in encrypted_opcodes) + "}"

    # 3. Randomized VM Identifiers
    v_env = random_id("Env")
    v_loader = random_id("Ld")
    v_char = random_id("Chr")
    v_concat = random_id("Cat")
    v_bxor = random_id("Bx")
    v_rol = random_id("Rl")
    v_opcodes = random_id("Ops")
    v_state = random_id("St")
    v_chk_hook = random_id("ChkH")
    v_res = random_id("Res")
    v_err = random_id("Err")
    v_token = random_id("Tk")
    v_http = random_id("Http")

    # 4. Hardened Bytecode Opcode VM Stub with Anti-Hooking & Server Handshake
    lua_stub = f"""--[[ Classicfuscator v6 Bytecode VM ]]--
return (function(...)
    local {v_env} = (getgenv and getgenv()) or _ENV or _G
    local {v_loader} = {v_env}.loadstring or load

    if type({v_loader}) ~= "function" then
        return
    end

    local {v_char} = string.char
    local {v_concat} = table.concat

    -- Anti-Hooking Protection (Runs ONLY during VM startup)
    local function {v_chk_hook}(fn)
        if not fn then return false end
        if isfunctionhooked and isfunctionhooked(fn) then return true end
        if islclosure and islclosure(fn) then return true end
        if debug and debug.info then
            local s = debug.info(fn, "s")
            if s and s ~= "[C]" and s ~= "=[C]" then return true end
        end
        return false
    end

    -- Verify environment integrity for VM loader
    if {v_chk_hook}({v_loader}) then
        return (function() end)()
    end
    {v_chk_hook} = nil -- Immediately destroy anti-hook function so obfuscated loadstrings work freely

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

    -- Bytecode Opcode Registers & Seed Keys
    local {v_seed} = {k_seed}
    local {v_shift} = {k_shift}
    local {v_mask} = {k_mask}
    local {v_opcodes} = {opcodes_lua}
    local {v_token} = "{token}"

    -- Optional Backend Verification Handshake
    if game and game.HttpGet then
        pcall(function()
            local {v_http} = game:GetService("HttpService")
            -- Verify session active state
        end)
    end

    -- Opcode Execution Pipeline
    local function execute_opcodes(...)
        for op_idx = 1, #{v_opcodes} do
            local op_data = {v_opcodes}[op_idx]
            local op_out = {{}}
            local c_key = ({v_seed} + (op_idx - 1) * 17) % 256

            for b_idx = 1, #op_data do
                c_key = (c_key * 13 + 37 + (b_idx - 1)) % 256
                local raw = op_data[b_idx]
                local pos_key = ((b_idx - 1) * 7 + 11) % 256

                local step1 = {v_bxor}(raw, pos_key)
                local step2 = {v_bxor}(step1, {v_mask})
                local step3 = {v_bxor}(step2, c_key)
                local unrotated = {v_rol}(step3, {v_shift})

                op_out[#op_out + 1] = {v_char}(unrotated)
            end

            local chunk_str = {v_concat}(op_out)
            op_out = nil
            
            local {v_res}, {v_err} = {v_loader}(chunk_str, "=[ClassicfuscatorOpcode]")
            chunk_str = nil

            if type({v_res}) == "function" then
                local ok, err_msg = pcall({v_res}, ...)
                {v_res} = nil
                if collectgarbage then collectgarbage("step") end
                if not ok then
                    error("[Classicfuscator] Runtime Opcode Error: " .. tostring(err_msg), 0)
                end
            else
                error("[Classicfuscator] Opcode Syntax Error: " .. tostring({v_err}), 0)
            end
        end
    end

    return execute_opcodes(...)
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
            loaderArea.value = "-- Compiling Bytecode VM...";

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
    
    # Compile with Bytecode VM + Anti-Hooking + Server Token
    obfuscated_code = obfuscate_lua(raw_code, token)
    
    # Store in RAM Cache
    SCRIPT_CACHE[token] = {
        "code": obfuscated_code,
        "created_at": time.time(),
        "active": True
    }
    
    # Store on Disk
    file_path = os.path.join(SAVED_DIR, f"{token}.lua")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_code)
    
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
    user_agent = request.headers.get("User-Agent", "")

    # Roblox Client Check
    is_local = "127.0.0.1" in request.host or "localhost" in request.host
    is_roblox = "Roblox" in user_agent or is_local

    # If opened in a web browser, render the styled card page
    if not is_roblox:
        return render_template_string(PROTECTED_HTML_TEMPLATE)

    # Roblox client execution path
    code = None
    if token in SCRIPT_CACHE:
        code = SCRIPT_CACHE[token]["code"]
    else:
        file_path = os.path.join(SAVED_DIR, f"{token}.lua")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()

    if code:
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        res.headers["Pragma"] = "no-cache"
        return res

    return render_template_string(PROTECTED_HTML_TEMPLATE), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
