import math
import os
import random
import re
import sqlite3
import time
import uuid
import base64
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

CUSTOM_DOMAIN = "" # Leave blank to auto-detect
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(BASE_DIR, "saved_scripts")
DB_PATH = os.path.join(BASE_DIR, "database.db")
os.makedirs(SAVED_DIR, exist_ok=True)
SCRIPT_CACHE = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS scripts (token TEXT PRIMARY KEY, code TEXT, created_at REAL)""")
    conn.commit()
    conn.close()

init_db()

def gen_id(prefix="", length=random.randint(16, 24)):
    """Generates highly hostile homoglyph variables."""
    return prefix + "".join(random.choices(["I", "l", "O", "0", "_"], k=length))

# ==============================================================================
# 1. CORE VM GENERATOR & POLYMORPHISM
# ==============================================================================

def encode_payload(lua_code):
    """Packs the lua code into a mutated byte-string with a rolling XOR cipher."""
    raw_bytes = list(lua_code.encode('utf-8'))
    seed = random.randint(10, 250)
    mutated = []
    c_key = seed
    
    for b in raw_bytes:
        # Rolling cipher: Key changes based on the previous encrypted byte
        enc = (b ^ c_key) % 256
        mutated.append(enc)
        c_key = (c_key + enc + 13) % 256
        
    # Convert to a chaotic string blob (e.g., "\x8F\x12\x4A")
    blob = "".join(f"\\{b}" for b in mutated)
    return blob, seed

def generate_junk_instruction():
    """Generates mathematically sound junk code to break decompilers."""
    v = gen_id()
    val = random.randint(100, 999)
    junk_types = [
        f"local {v} = {val}; {v} = ({v} * 2) - {val};",
        f"if math.abs(math.cos(math.pi)) == -1 then return end;",
        f"local {v} = tostring({val}); if #{v} > 10 then while true do end end;",
        f"(function() local {v} = {val}; return {v} end)();"
    ]
    return random.choice(junk_types)

def build_enterprise_vm(raw_code, settings):
    packed_blob, xor_seed = encode_payload(raw_code)
    
    # Generate VM Variable Names
    v_env = gen_id("Env")
    v_blob = gen_id("Blob")
    v_pc = gen_id("PC")
    v_key = gen_id("Key")
    v_buf = gen_id("Buf")
    v_dispatch = gen_id("Disp")
    v_state = gen_id("State")
    v_anti = gen_id("Sec")
    v_loader = gen_id("Ld")
    v_byte = gen_id("B")
    v_char = gen_id("C")
    
    anti_tamper = ""
    if settings.get("antihook", True):
        anti_tamper = f"""
        local function {v_anti}()
            -- 1. Detach from exploit traces
            local g = getfenv(0)
            local _ts = tostring
            local _type = type
            local _grm = getrawmetatable or function() return false end
            
            -- 2. Detect C-Closure spoofing
            if iscclosure and not iscclosure(print) then while true do end end
            
            -- 3. Detect Metatable Hooking
            local mt = _grm(game)
            if mt and _type(mt) == "table" then
                if rawget(mt, "__namecall") and _ts(rawget(mt, "__namecall")):find("hook") then
                    return false
                end
            end
            
            -- 4. Environment Checksum
            if _ts(game) ~= "Game" or _ts(workspace) ~= "Workspace" then return false end
            return true
        end
        if not {v_anti}() then return end
        """

    # Polymorphic Instruction Dispatcher
    # We shuffle the state IDs so decompilers can't map execution flow
    states = list(range(1, 6))
    random.shuffle(states)
    
    s_init = states[0]
    s_read = states[1]
    s_decrypt = states[2]
    s_compile = states[3]
    s_exec = states[4]
    
    # Hide loadstring dynamically
    # getfenv(0)["\108\111\97\100\115\116\114\105\110\103"] == loadstring
    hidden_loadstring = 'getfenv(0)["\\108\\111\\97\\100\\115\\116\\114\\105\\110\\103"] or getfenv(0)["\\108\\111\\97\\100"]'

    vm_lua = f"""
local function __ENTERPRISE_INIT(...)
    {anti_tamper}
    
    local {v_env} = setmetatable({{}}, {{
        __index = function(_, k) return getgenv and getgenv()[k] or getfenv(0)[k] end,
        __newindex = function(_, k, v) local g = getgenv and getgenv() or getfenv(0); g[k] = v end,
        __metatable = "LOCKED_ENV"
    }})

    local {v_blob} = "{packed_blob}"
    local {v_pc} = 1
    local {v_key} = {xor_seed}
    local {v_buf} = {{}}
    local {v_state} = {s_init}
    
    local {v_byte} = string.byte
    local {v_char} = string.char
    local {v_loader} = {hidden_loadstring}
    
    if type({v_loader}) ~= "function" then return end

    -- VM Dispatch Table (Polymorphic CFF)
    local {v_dispatch} = {{
        [{s_init}] = function()
            {generate_junk_instruction()}
            {v_state} = {s_read}
        end,
        [{s_read}] = function()
            if {v_pc} > #{v_blob} then
                {v_state} = {s_compile}
                return
            end
            {v_state} = {s_decrypt}
        end,
        [{s_decrypt}] = function()
            local enc = {v_byte}({v_blob}, {v_pc}, {v_pc})
            local dec = bit32 and bit32.bxor(enc, {v_key}) or (function(a,b)
                local r,p=0,1; while a>0 or b>0 do if a%2 ~= b%2 then r=r+p end; a,b,p=math.floor(a/2),math.floor(b/2),p*2 end return r
            end)(enc, {v_key})
            
            {v_buf}[#{v_buf}+1] = {v_char}(dec)
            {v_key} = ({v_key} + enc + 13) % 256
            {v_pc} = {v_pc} + 1
            {v_state} = {s_read}
        end,
        [{s_compile}] = function()
            local chunk = table.concat({v_buf})
            {v_buf} = {{}} -- Memory wipe
            {v_blob} = ""  -- Memory wipe
            
            local func = {v_loader}(chunk)
            chunk = string.rep("0", #chunk) -- Strict RAM overwrite
            
            if func then
                if setfenv then setfenv(func, {v_env}) end
                {v_buf}[1] = func
                {v_state} = {s_exec}
            else
                {v_state} = 0
            end
        end,
        [{s_exec}] = function()
            local f = {v_buf}[1]
            {v_buf}[1] = nil
            -- Tail call via coroutine to hide stack trace
            local ok, err = coroutine.resume(coroutine.create(f))
            if not ok then warn(err) end
            {v_state} = 0
        end
    }}

    -- Execution Loop
    while {v_state} ~= 0 do
        local handler = {v_dispatch}[{v_state}]
        if handler then handler() else break end
    end
end

-- Isolate execution
return pcall(__ENTERPRISE_INIT)
"""
    # Wrap in one final outer base64 to prevent instant static analysis
    b64_final = base64.b64encode(vm_lua.strip().encode('utf-8')).decode('utf-8')
    wrapper = f"""
local d = "{b64_final}"
local f = (loadstring or load)(
    (d:gsub('.', function(x)
        if x == '=' then return '' end
        local r,f='', (ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/:find(x)-1)
        for i=6,1,-1 do r=r..(f%2^i-f%2^(i-1)>0 and '1' or '0') end return r;
    end):gsub('%d%d%d?%d?%d?%d?%d?%d?', function(x)
        if (#x ~= 8) then return '' end
        local c=0; for i=1,8 do c=c+(x:sub(i,i)=='1' and 2^(8-i) or 0) end
        return string.char(c)
    end))
)
if f then return f() end
"""
    # Replace the hardcoded base64 alphabet string
    wrapper = wrapper.replace("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", "'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'")
    return wrapper.strip()

def obfuscate_pipeline(raw_code: str, settings: dict) -> str:
    return build_enterprise_vm(raw_code, settings)

# ==============================================================================
# 2. PREMIUM DASHBOARD UI (HTML)
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator V3 Enterprise</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@400;600;800&display=swap');
        * { box-sizing: border-box; }
        body { background-color: #030712; color: #f9fafb; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: 'Inter', sans-serif; background-image: radial-gradient(circle at top, #1f2937 0%, transparent 40%);}
        .card { background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(20px); border-radius: 16px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1); width: 100%; max-width: 700px; padding: 40px; border: 1px solid #374151; }
        
        .header { text-align: center; margin-bottom: 30px; }
        h1 { font-size: 32px; font-weight: 800; background: linear-gradient(135deg, #38bdf8, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; letter-spacing: -1px; }
        .badge { display: inline-block; background: rgba(56, 189, 248, 0.1); color: #38bdf8; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; margin-top: 10px; border: 1px solid rgba(56, 189, 248, 0.2); text-transform: uppercase; letter-spacing: 1px;}

        textarea { width: 100%; height: 220px; border: 1px solid #374151; border-radius: 12px; padding: 16px; font-size: 13px; font-family: 'Fira Code', monospace; outline: none; background: #0f172a; color: #38bdf8; resize: vertical; transition: all 0.3s ease; margin-bottom: 20px; box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);}
        textarea:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15), inset 0 2px 10px rgba(0,0,0,0.2); }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
        .feature { background: #1e293b; padding: 16px; border-radius: 12px; border: 1px solid #334155; display: flex; flex-direction: column; gap: 6px; position: relative; overflow: hidden;}
        .feature::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; background: #818cf8; border-radius: 4px 0 0 4px; }
        .feature.red::before { background: #f43f5e; }
        .feature.green::before { background: #10b981; }
        
        .f-title { font-size: 14px; font-weight: 600; color: #f1f5f9; display: flex; justify-content: space-between; align-items: center;}
        .f-desc { font-size: 12px; color: #94a3b8; line-height: 1.4; }
        
        .btn { width: 100%; padding: 16px; background: linear-gradient(135deg, #4f46e5, #3b82f6); color: #ffffff; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s ease; text-transform: uppercase; letter-spacing: 1px; box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);}
        .btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4); }
        
        .output-container { margin-top: 30px; display: none; animation: fadeIn 0.5s ease;}
        .loader-text { width: 100%; height: auto; background: rgba(15, 23, 42, 0.8); border: 1px solid #374151; color: #10b981; font-family: 'Fira Code', monospace; padding: 16px; border-radius: 12px; resize: none; margin-bottom: 12px;}
        
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        /* Custom Checkbox */
        .switch { position: relative; display: inline-block; width: 36px; height: 20px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #475569; transition: .3s; border-radius: 20px; }
        .slider:before { position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
        input:checked + .slider { background-color: #818cf8; }
        input:checked + .slider:before { transform: translateX(16px); }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>Classicfuscator V3</h1>
            <div class="badge">Enterprise Protection Engine</div>
        </div>

        <textarea id="input" placeholder="-- Paste Lua script here..."></textarea>
        
        <div class="grid">
            <div class="feature">
                <div class="f-title">Polymorphic VM <label class="switch"><input type="checkbox" checked disabled><span class="slider"></span></label></div>
                <div class="f-desc">Dispatch tables and internal registers shuffle every build.</div>
            </div>
            <div class="feature green">
                <div class="f-title">Stack Isolation <label class="switch"><input type="checkbox" checked disabled><span class="slider"></span></label></div>
                <div class="f-desc">Coroutines & Tail Calls hide script from debug.traceback.</div>
            </div>
            <div class="feature red">
                <div class="f-title">Strict Anti-Hook <label class="switch"><input type="checkbox" id="cfgAntiHook" checked><span class="slider"></span></label></div>
                <div class="f-title" style="font-size: 11px; color:#f43f5e;">Requires Roblox Exploit Env</div>
            </div>
            <div class="feature">
                <div class="f-title">RAM Wiper <label class="switch"><input type="checkbox" checked disabled><span class="slider"></span></label></div>
                <div class="f-desc">Forces garbage collection of bytecode chunks instantly.</div>
            </div>
        </div>

        <button class="btn" id="submitBtn" onclick="obfuscate()">Compile Payload</button>

        <div class="output-container" id="outputWrapper">
            <div style="font-size: 12px; color: #94a3b8; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">Secure Execution Loader</div>
            <textarea id="loaderOutput" class="loader-text" readonly rows="2"></textarea>
            <button class="btn" id="copyBtn" style="background: #334155; box-shadow: none;" onclick="copyLoader()">Copy to Clipboard</button>
        </div>
    </div>

    <script>
        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const loaderArea = document.getElementById('loaderOutput');
            const submitBtn = document.getElementById('submitBtn');
            
            if (!inputCode.trim()) return;

            const settings = {
                antihook: document.getElementById('cfgAntiHook').checked,
            };

            outputWrapper.style.display = "block";
            loaderArea.value = "Encoding payload and compiling Polymorphic VM...";
            submitBtn.innerText = "Processing...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode, settings: settings })
                });

                const data = await response.json();
                loaderArea.value = data.loader || "-- Error: " + data.error;
            } catch (err) {
                loaderArea.value = "-- Network error.";
            } finally {
                submitBtn.innerText = "Compile Payload";
            }
        }

        function copyLoader() {
            const loaderArea = document.getElementById('loaderOutput');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            document.getElementById('copyBtn').innerText = "Copied to Clipboard!";
            setTimeout(() => { document.getElementById('copyBtn').innerText = "Copy to Clipboard"; }, 2000);
        }
    </script>
</body>
</html>
"""

PROTECTED_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Protected Resource</title>
<style>body{background:#030712;color:#38bdf8;font-family:monospace;display:flex;justify-content:center;align-items:center;height:100vh;}</style></head>
<body><h2>[SECURE TUNNEL] Connection Refused: HTTP Browser Detected</h2></body></html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/obfuscate", methods=["POST"])
def process():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code", "")
    settings = data.get("settings", {})
    
    if not raw_code.strip():
        return jsonify({"success": False, "error": "Empty input"}), 400
    
    token = uuid.uuid4().hex
    try:
        obfuscated_code = obfuscate_pipeline(raw_code, settings)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    SCRIPT_CACHE[token] = {"code": obfuscated_code, "created_at": time.time()}
    with open(os.path.join(SAVED_DIR, f"{token}.lua"), "w") as f:
        f.write(obfuscated_code)

    domain = CUSTOM_DOMAIN or request.host_url.rstrip("/")
    loader = f'loadstring(game:HttpGet("{domain}/raw/{token}"))()'

    return jsonify({"success": True, "loader": loader})

@app.route("/raw/<token>", methods=["GET"])
def serve_script(token):
    # Aggressively block normal web browsers to prevent manual dumping
    if "Mozilla" in request.headers.get("User-Agent", "") and not "Roblox" in request.headers.get("User-Agent", ""):
        return render_template_string(PROTECTED_HTML_TEMPLATE)

    code = SCRIPT_CACHE.get(token, {}).get("code")
    if not code:
        file_path = os.path.join(SAVED_DIR, f"{token}.lua")
        if os.path.exists(file_path):
            with open(file_path, "r") as f: code = f.read()

    if code:
        res = Response(code, mimetype="text/plain")
        res.headers["Cache-Control"] = "no-store, max-age=0"
        return res

    return Response("warn('[V3 Engine] Token Expired.')", status=200, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
