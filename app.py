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
    body = "".join(random.choices(chars, k=random.randint(20, 30)))
    return f"{prefix}_{body}"


def ror(val, count, bits=8):
    """Rotate Right for 8-bit integer."""
    return ((val >> count) | (val << (bits - count))) & 0xFF


def obfuscate_lua(code: str) -> str:
    if not code.strip():
        return "-- Error: Empty script provided."

    # 1. Polynomial Cipher Keys & Rolling State Seed
    k_seed = random.randint(10000, 999999)
    k_mult = random.randint(5, 29) * 2 + 1
    k_inc = random.randint(1, 255)
    k_shift = random.randint(1, 7)
    k_mask = random.randint(16, 240)
    k_poly1 = random.randint(3, 17)

    # 2. Rolling-Key Positional Encryption
    raw_bytes = list(code.encode("utf-8"))
    encrypted_bytes = []
    
    current_key = k_seed
    for idx, byte in enumerate(raw_bytes):
        current_key = (current_key * k_mult + k_inc + idx * k_poly1) % 256
        rotated = ror(byte, k_shift)
        pos_key = (idx * 7 + 13) % 256
        enc = (rotated ^ current_key ^ k_mask ^ pos_key) % 256
        encrypted_bytes.append(enc)

    # 3. Dynamic Sub-Table Chunking
    chunk_size = random.randint(12, 28)
    chunks = [
        encrypted_bytes[i : i + chunk_size]
        for i in range(0, len(encrypted_bytes), chunk_size)
    ]
    chunks_lua = "{" + ",".join("{" + ",".join(map(str, c)) + "}" for c in chunks) + "}"

    # 4. Randomized VM State Identifiers
    st_init = random.randint(100, 199)
    st_check = random.randint(200, 299)
    st_unpack = random.randint(300, 399)
    st_exec = random.randint(400, 499)
    st_trap = random.randint(500, 599)

    # 5. Identifier Names Generator
    v_seed = random_id("S")
    v_mult = random_id("M")
    v_inc = random_id("C")
    v_shift = random_id("Sh")
    v_mask = random_id("Mk")
    v_poly1 = random_id("Py")
    v_chunks = random_id("Data")
    v_out = random_id("Out")
    v_state = random_id("St")
    v_char = random_id("Chr")
    v_concat = random_id("Cat")
    v_env = random_id("Env")
    v_loader = random_id("Ld")
    v_res = random_id("Res")
    v_err = random_id("Err")
    v_idx = random_id("Idx")
    v_bxor = random_id("Bx")
    v_rol = random_id("Rl")
    v_disp = random_id("Disp")
    v_inv_chk = random_id("Inv")

    # 6. Hardened VM State-Machine Stub
    lua_stub = f"""--[[ Classicfuscator v5 Hardened VM ]]--
return (function(...)
    local {v_env} = (getgenv and getgenv()) or _ENV or _G
    local {v_loader} = {v_env}.loadstring or load

    if type({v_loader}) ~= "function" then
        return
    end

    local {v_char} = string.char
    local {v_concat} = table.concat

    -- Safe Bitwise XOR Engine with Pure Lua Fallback
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

    -- Mathematical Invariant Integrity Engine (Compatible with All Executors)
    local function {v_inv_chk}()
        local m_test = (math.floor(math.sin(1.57079632679) * 100) == 100)
        local c_test = (math.cos(0) == 1)
        local b_test = ({v_bxor}(15, 7) == 8)
        return m_test and c_test and b_test
    end

    -- Virtual Machine State Variables
    local {v_seed} = {k_seed}
    local {v_mult} = {k_mult}
    local {v_inc} = {k_inc}
    local {v_shift} = {k_shift}
    local {v_mask} = {k_mask}
    local {v_poly1} = {k_poly1}
    local {v_chunks} = {chunks_lua}

    local {v_out} = {{}}
    local {v_state} = {v_seed}
    local {v_idx} = 0
    local {v_disp} = {st_init}

    -- VM State Machine Dispatcher
    while {v_disp} ~= 0 do
        if {v_disp} == {st_init} then
            if {v_inv_chk}() then
                {v_disp} = {st_check}
            else
                {v_disp} = {st_trap}
            end
        elseif {v_disp} == {st_check} then
            {v_disp} = {st_unpack}
        elseif {v_disp} == {st_unpack} then
            for c_idx = 1, #{v_chunks} do
                local chunk = {v_chunks}[c_idx]
                for b_idx = 1, #chunk do
                    {v_state} = ({v_state} * {v_mult} + {v_inc} + {v_idx} * {v_poly1}) % 256
                    local raw = chunk[b_idx]
                    local pos_key = ({v_idx} * 7 + 13) % 256
                    
                    local step1 = {v_bxor}(raw, pos_key)
                    local step2 = {v_bxor}(step1, {v_mask})
                    local step3 = {v_bxor}(step2, {v_state})
                    local unrotated = {v_rol}(step3, {v_shift})
                    
                    {v_out}[#{v_out} + 1] = {v_char}(unrotated)
                    {v_idx} = {v_idx} + 1
                end
            end
            {v_disp} = {st_exec}
        elseif {v_disp} == {st_exec} then
            local payload_str = {v_concat}({v_out})
            
            -- Immediate Memory Sanitization
            {v_out} = nil
            {v_chunks} = nil
            if collectgarbage then collectgarbage("collect") end

            local {v_res}, {v_err} = {v_loader}(payload_str, "=[ClassicfuscatorVM]")
            payload_str = nil

            if type({v_res}) == "function" then
                {v_disp} = 0
                return {v_res}(...)
            else
                {v_disp} = 0
                error("[Classicfuscator] Syntax error in payload: " .. tostring({v_err}), 0)
            end
        elseif {v_disp} == {st_trap} then
            {v_disp} = 0
            return (function() end)()
        end
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
        const fileInput = document.getElementById('luaFileInput');

        // Drag & Drop event handlers
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
            loaderArea.value = "-- Processing Hardened VM Cipher...";

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
    
    obfuscated_code = obfuscate_lua(raw_code)
    
    # Dynamic 32-character Hex Token
    token = uuid.uuid4().hex
    
    # Store in RAM Cache
    SCRIPT_CACHE[token] = {
        "code": obfuscated_code,
        "created_at": time.time()
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
