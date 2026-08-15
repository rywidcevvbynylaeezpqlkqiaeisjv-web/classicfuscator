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
    return prefix + "".join(random.choices(["I", "l", "1", "_"], k=length))

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
        enc = (b ^ c_key) % 256
        mutated.append(enc)
        c_key = (c_key + enc + 13) % 256
        
    blob = "".join(f"\\{b}" for b in mutated)
    return blob, seed

def generate_junk_instruction():
    """Generates mathematically sound junk code."""
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
            local _ts = tostring
            local _type = type
            local _grm = getrawmetatable or function() return false end
            
            if iscclosure and not iscclosure(print) then while true do end end
            
            local s, mt = pcall(function() return _grm(game) end)
            if s and mt and _type(mt) == "table" then
                local nc = rawget(mt, "__namecall")
                if nc and _type(nc) == "function" and _ts(nc):find("hook") then
                    return false
                end
            end
            return true
        end
        if not {v_anti}() then return end
        """

    states = list(range(1, 6))
    random.shuffle(states)
    s_init, s_read, s_decrypt, s_compile, s_exec = states

    vm_lua = f"""
local function __ENTERPRISE_INIT(...)
    {anti_tamper}
    
    local {v_env} = setmetatable({{}}, {{
        __index = function(_, k) 
            local g = getgenv and getgenv() or _G or {{}}
            local f = getfenv(0) or {{}}
            return g[k] or f[k]
        end,
        __newindex = function(_, k, v) 
            local g = getgenv and getgenv() or getfenv(0)
            if g then g[k] = v end
        end,
        __metatable = "LOCKED_ENV"
    }})

    local {v_blob} = "{packed_blob}"
    local {v_pc} = 1
    local {v_key} = {xor_seed}
    local {v_buf} = {{}}
    local {v_state} = {s_init}
    
    local {v_byte} = string.byte
    local {v_char} = string.char
    
    -- Mobile Executor Safe Loadstring Fetch
    local {v_loader} = nil
    if getgenv and getgenv()["\108\111\97\100\115\116\114\105\110\103"] then 
        {v_loader} = getgenv()["\108\111\97\100\115\116\114\105\110\103"] 
    end
    if not {v_loader} and loadstring then {v_loader} = loadstring end
    if not {v_loader} and load then {v_loader} = load end
    
    if type({v_loader}) ~= "function" then return warn("Executor Missing Loadstring") end

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
            {v_buf} = {{}}
            {v_blob} = ""
            
            local func, err = {v_loader}(chunk)
            chunk = string.rep("0", #chunk) 
            
            if func then
                if setfenv then pcall(setfenv, func, {v_env}) end
                {v_buf}[1] = func
                {v_state} = {s_exec}
            else
                warn(err)
                {v_state} = 0
            end
        end,
        [{s_exec}] = function()
            local f = {v_buf}[1]
            {v_buf}[1] = nil
            local ok, err = coroutine.resume(coroutine.create(f))
            if not ok then warn(err) end
            {v_state} = 0
        end
    }}

    while {v_state} ~= 0 do
        local handler = {v_dispatch}[{v_state}]
        if handler then handler() else break end
    end
end

return pcall(__ENTERPRISE_INIT)
"""
    b64_final = base64.b64encode(vm_lua.strip().encode('utf-8')).decode('utf-8')
    wrapper = f"""
local ls = nil
if getgenv and getgenv().loadstring then ls = getgenv().loadstring end
if not ls and loadstring then ls = loadstring end
if not ls and load then ls = load end
if type(ls) ~= "function" then return warn("Executor does not support loadstring") end

local d = "{b64_final}"
local step1 = d:gsub('.', function(x)
    if x == '=' then return '' end
    local r,f='', ('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/':find(x)-1)
    for i=6,1,-1 do r=r..(f%2^i-f%2^(i-1)>0 and '1' or '0') end return r;
end)
local step2 = step1:gsub('%d%d%d?%d?%d?%d?%d?%d?', function(x)
    if (#x ~= 8) then return '' end
    local c=0; for i=1,8 do c=c+(x:sub(i,i)=='1' and 2^(8-i) or 0) end
    return string.char(c)
end)

local f, err = ls(step2)
if type(f) == "function" then
    return f()
else
    warn(err)
end
"""
    return wrapper.strip()

# ==============================================================================
# 2. LIGHT THEME DASHBOARD UI (ORIGINAL)
# ==============================================================================

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
            max-width: 560px; 
            padding: 36px 32px; 
            border: 1px solid #eef0f4; 
        }
        h1 { 
            font-size: 28px; 
            font-weight: 700; 
            color: #1a1a1a; 
            margin: 0 0 20px 0; 
            letter-spacing: -0.3px;
        }
        
        .tab-nav {
            display: flex;
            gap: 8px;
            background: #f1f5f9;
            padding: 4px;
            border-radius: 12px;
            margin-bottom: 24px;
        }
        .tab-btn {
            flex: 1;
            padding: 10px 16px;
            border: none;
            background: transparent;
            color: #64748b;
            font-size: 14px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .tab-btn.active {
            background: #ffffff;
            color: #0070f3;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .file-upload-box {
            border: 2px dashed #0070f3;
            border-radius: 12px;
            padding: 22px 20px;
            background-color: #ffffff;
            margin-bottom: 18px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .file-upload-box:hover, .file-upload-box.drag-over {
            background-color: #f0f7ff;
            border-color: #0052cc;
        }
        .file-upload-title {
            font-size: 15px;
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 4px;
            display: block;
        }
        .file-upload-subtext {
            font-size: 13px;
            color: #64748b;
            margin: 0;
        }
        .or-text {
            font-size: 14px;
            font-weight: 500;
            color: #1e293b;
            margin-bottom: 10px;
        }
        textarea { 
            width: 100%; 
            height: 160px;
            border: 1px solid #dcdfe6; 
            border-radius: 12px; 
            padding: 14px; 
            font-size: 13.5px; 
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
            font-size: 15px; 
            font-weight: 600; 
            cursor: pointer; 
            margin-top: 18px; 
            transition: background-color 0.2s ease;
            box-shadow: 0 4px 12px rgba(0, 112, 243, 0.2);
        }
        .btn:hover { background-color: #005bb5; }
        
        .output-container { margin-top: 22px; display: none; }
        .loader-box { 
            background: #f8fafc; 
            border: 1px solid #e2e8f0; 
            border-radius: 12px; 
            padding: 14px; 
        }
        .section-label { 
            font-size: 13px; 
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
            font-size: 12.5px;
            padding: 12px;
            white-space: nowrap;
            overflow-x: auto;
            resize: none;
        }

        .setting-group {
            margin-bottom: 18px;
            background: #f8fafc;
            padding: 14px 16px;
            border-radius: 12px;
            border: 1px solid #eef2f6;
        }
        .setting-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .setting-title {
            font-size: 14px;
            font-weight: 600;
            color: #1e293b;
        }
        .setting-desc {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }
        .setting-select, .setting-input {
            padding: 8px 12px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 13px;
            outline: none;
            background: #ffffff;
            color: #1e293b;
        }
        
        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #cbd5e1;
            transition: .3s;
            border-radius: 24px;
        }
        .slider:before {
            position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }
        input:checked + .slider { background-color: #0070f3; }
        input:checked + .slider:before { transform: translateX(20px); }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator</h1>

        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('obfuscatorTab', this)">Category 1: Obfuscator</button>
            <button class="tab-btn" onclick="switchTab('settingsTab', this)">Category 2: Settings</button>
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
                <div class="setting-header">
                    <div>
                        <div class="setting-title">Polymorphic VM Structure</div>
                        <div class="setting-desc">Automatically enabled in Enterprise build.</div>
                    </div>
                    <label class="switch"><input type="checkbox" checked disabled><span class="slider"></span></label>
                </div>
            </div>

            <div class="setting-group">
                <div class="setting-header">
                    <div>
                        <div class="setting-title">Anti-Hook & Sentinel Matrix</div>
                        <div class="setting-desc">Inspects callstack, C-closures, and catches hooks.</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="cfgAntiHook" checked>
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <div class="setting-group">
                <div class="setting-title" style="margin-bottom: 6px;">Custom Watermark Header</div>
                <input type="text" id="cfgWatermark" class="setting-input" style="width: 100%;" placeholder="e.g. Classicfuscator Enterprise">
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
            
            if (!inputCode.trim()) {
                return;
            }

            const settings = {
                antihook: document.getElementById('cfgAntiHook').checked,
                watermark: document.getElementById('cfgWatermark').value
            };

            outputWrapper.style.display = "block";
            loaderArea.value = "-- Validating syntax & compiling Polymorphic VM...";
            submitBtn.innerText = "Processing...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode, settings: settings })
                });

                const data = await response.json();
                if (response.ok && data.loader) {
                    loaderArea.value = data.loader;
                } else {
                    loaderArea.value = "-- " + (data.error || "Syntax error detected.");
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
        body { background-color: #f2f4f8; color: #1e293b; margin: 0; padding: 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04); width: 100%; max-width: 440px; padding: 40px 28px; border: 1px solid #eef0f4; text-align: center; }
        h1 { font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 0 0 10px 0; }
        p { font-size: 15px; color: #64748b; margin: 0; }
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
    settings = data.get("settings", {})
    
    if not raw_code.strip():
        return jsonify({"success": False, "error": "Empty input"}), 400
    
    token = uuid.uuid4().hex
    try:
        obfuscated_code = build_enterprise_vm(raw_code, settings)
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
    if request.headers.get("Sec-Fetch-Dest", "") == "document":
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

    return Response("warn('[Classicfuscator] Token Expired.')", status=200, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
