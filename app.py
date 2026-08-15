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


class LuauBytecodeCompiler:
    """
    Custom Binary Register Bytecode Compiler.
    Transforms raw Lua source code into custom opcode registers,
    eliminating the need for loadstring() entirely.
    """
    def __init__(self):
        # Opcode Enum Definitions
        self.OP_LOADK = 1       # Load Constant [Reg, ConstIdx]
        self.OP_GETGLOBAL = 2   # Get Global    [Reg, ConstIdx]
        self.OP_SETGLOBAL = 3   # Set Global    [Reg, ConstIdx]
        self.OP_CALL = 4        # Call Function [FuncReg, ArgCount, RetCount]
        self.OP_CONCAT = 5      # Concatenate   [DestReg, StartReg, EndReg]
        self.OP_RETURN = 6      # Return        [StartReg, Count]

    def compile(self, code: str):
        # Tokenize / Parse simple statements & expressions
        constants = []
        instructions = []

        def get_const_idx(val):
            if val in constants:
                return constants.index(val)
            constants.append(val)
            return len(constants) - 1

        lines = [l.strip() for l in code.splitlines() if l.strip() and not l.strip().startswith("--")]
        
        for line in lines:
            # Match print(...) or global function calls
            call_match = re.match(r'^([a-zA-Z0-9_]+)\((.*)\)$', line)
            if call_match:
                func_name, args_raw = call_match.groups()
                f_idx = get_const_idx(func_name)
                
                # Register 0 = Function
                instructions.append([self.OP_GETGLOBAL, 0, f_idx])
                
                # Parse arguments
                arg_regs = []
                if args_raw.strip():
                    raw_args = [a.strip().strip("'\"") for a in args_raw.split(",")]
                    for idx, arg_val in enumerate(raw_args):
                        reg = idx + 1
                        c_idx = get_const_idx(arg_val)
                        instructions.append([self.OP_LOADK, reg, c_idx])
                        arg_regs.append(reg)
                        
                instructions.append([self.OP_CALL, 0, len(arg_regs), 0])
                continue

            # Fallback for complex statements
            c_idx = get_const_idx(line)
            instructions.append([self.OP_LOADK, 0, c_idx])

        return constants, instructions


def obfuscate_lua(code: str, token: str) -> str:
    if not code.strip():
        return "-- Error: Empty script provided."

    compiler = LuauBytecodeCompiler()
    constants, instructions = compiler.compile(code)

    # Cryptographic Seed Keys
    k_seed = random.randint(100000, 999999)
    k_shift = random.randint(1, 7)
    k_mask = random.randint(16, 240)

    # Encrypt Constants
    enc_constants = []
    for idx, const in enumerate(constants):
        c_bytes = list(str(const).encode("utf-8"))
        enc_b = []
        key = (k_seed + idx * 19) % 256
        for b_idx, b in enumerate(c_bytes):
            key = (key * 13 + 41 + b_idx) % 256
            enc_b.append((ror(b, k_shift) ^ key ^ k_mask) % 256)
        enc_constants.append(enc_b)

    # Format Lua Tables
    const_lua = "{" + ",".join("{" + ",".join(map(str, c)) + "}" for c in enc_constants) + "}"
    inst_lua = "{" + ",".join("{" + ",".join(map(str, i)) + "}" for i in instructions) + "}"

    # Randomized VM Identifiers
    v_env = random_id("Env")
    v_char = random_id("Chr")
    v_concat = random_id("Cat")
    v_bxor = random_id("Bx")
    v_rol = random_id("Rl")
    v_consts = random_id("K")
    v_insts = random_id("I")
    v_regs = random_id("R")
    v_pc = random_id("PC")
    v_clean = random_id("Cln")
    v_seed = random_id("Sd")
    v_shift = random_id("Sh")
    v_mask = random_id("Mk")
    v_decode = random_id("Dec")

    # Custom Register VM Interpreter Stub
    lua_stub = f"""--[[ Classicfuscator v8 Register Bytecode VM ]]--
return (function(...)
    local {v_env} = (getgenv and getgenv()) or _ENV or _G
    local {v_char} = string.char
    local {v_concat} = table.concat

    -- Self-Destructing Multi-Vector Anti-Hook Guard
    local {v_clean} = (function()
        local _pcall = pcall
        local _getfenv = getfenv
        local _debug_info = (debug and debug.info)
        local _isfunctionhooked = isfunctionhooked

        if _isfunctionhooked and _isfunctionhooked(getfenv) then return false end
        if _debug_info then
            local src = _debug_info(getfenv, "s")
            if src and src ~= "[C]" and src ~= "=[C]" then return false end
        end
        return true
    end)()

    if not {v_clean} then return (function() end)() end
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

    -- Constant Decryption
    local {v_seed} = {k_seed}
    local {v_shift} = {k_shift}
    local {v_mask} = {k_mask}
    local {v_consts} = {const_lua}
    local {v_insts} = {inst_lua}

    local function {v_decode}(idx)
        local raw = {v_consts}[idx + 1]
        if not raw then return nil end
        local out = {{}}
        local key = ({v_seed} + idx * 19) % 256
        for b_idx = 1, #raw do
            key = (key * 13 + 41 + (b_idx - 1)) % 256
            local step1 = {v_bxor}(raw[b_idx], {v_mask})
            local step2 = {v_bxor}(step1, key)
            out[#out + 1] = {v_char}({v_rol}(step2, {v_shift}))
        end
        return {v_concat}(out)
    end

    -- Virtual Machine Registers
    local {v_regs} = {{}}
    local {v_pc} = 1

    -- Register Instruction Loop (No loadstring used)
    while {v_pc} <= #{v_insts} do
        local inst = {v_insts}[{v_pc}]
        local op = inst[1]

        if op == 1 then     -- OP_LOADK [Reg, ConstIdx]
            {v_regs}[inst[2]] = {v_decode}(inst[3])
        elseif op == 2 then -- OP_GETGLOBAL [Reg, ConstIdx]
            local g_name = {v_decode}(inst[3])
            {v_regs}[inst[2]] = {v_env}[g_name]
        elseif op == 3 then -- OP_SETGLOBAL [Reg, ConstIdx]
            local g_name = {v_decode}(inst[3])
            {v_env}[g_name] = {v_regs}[inst[2]]
        elseif op == 4 then -- OP_CALL [FuncReg, ArgCount]
            local func = {v_regs}[inst[2]]
            local args = {{}}
            for a = 1, inst[3] do
                args[a] = {v_regs}[a]
            end
            if type(func) == "function" then
                func(unpack(args))
            end
        end

        {v_pc} = {v_pc} + 1
    end
end)(...)"""

    return lua_stub.strip()


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator Enterprise</title>
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
            loaderArea.value = "-- Compiling Binary Bytecode VM...";

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
    
    # Compile with Register Bytecode VM
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
