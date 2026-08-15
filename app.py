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


def generate_password(length=45):
    """Generates a secure, random password of specified length."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


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

    k_seed = random.randint(10000, 999999)
    k_mult = random.randint(5, 29) * 2 + 1
    k_inc = random.randint(1, 255)
    k_shift = random.randint(1, 7)
    k_mask = random.randint(16, 240)
    k_poly1 = random.randint(3, 17)

    raw_bytes = list(code.encode("utf-8"))
    encrypted_bytes = []
    
    current_key = k_seed
    for idx, byte in enumerate(raw_bytes):
        current_key = (current_key * k_mult + k_inc + idx * k_poly1) % 256
        rotated = ror(byte, k_shift)
        pos_key = (idx * 7 + 13) % 256
        enc = (rotated ^ current_key ^ k_mask ^ pos_key) % 256
        encrypted_bytes.append(enc)

    chunk_size = random.randint(12, 28)
    chunks = [
        encrypted_bytes[i : i + chunk_size]
        for i in range(0, len(encrypted_bytes), chunk_size)
    ]
    chunks_lua = "{" + ",".join("{" + ",".join(map(str, c)) + "}" for c in chunks) + "}"

    st_init = random.randint(100, 199)
    st_check = random.randint(200, 299)
    st_unpack = random.randint(300, 399)
    st_exec = random.randint(400, 499)
    st_trap = random.randint(500, 599)

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

    lua_stub = f"""--[[ Classicfuscator v5 Hardened VM ]]--
return (function(...)
    local {v_env} = (getgenv and getgenv()) or _ENV or _G
    local {v_loader} = {v_env}.loadstring or load

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

    local function {v_inv_chk}()
        local m_test = (math.floor(math.sin(1.57079632679) * 100) == 100)
        local c_test = (math.cos(0) == 1)
        local b_test = ({v_bxor}(15, 7) == 8)
        return m_test and c_test and b_test
    end

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


# Original Light Theme Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator - Free Online Roblox & Luau Script Obfuscator</title>

    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #f0f7ff; color: #1e293b; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 12px 40px rgba(0, 112, 243, 0.08); width: 100%; max-width: 620px; padding: 36px; border: 1px solid #e2e8f0; position: relative; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        h1 { font-size: 26px; font-weight: 800; color: #0070f3; margin: 0; letter-spacing: -0.5px; }
        .form-group { margin-bottom: 18px; }
        .section-label { font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 8px; display: block; }
        textarea { width: 100%; height: 160px; border: 1px solid #cbd5e1; border-radius: 12px; padding: 14px; font-family: "Fira Code", monospace, sans-serif; font-size: 13px; resize: vertical; outline: none; background-color: #ffffff; color: #0f172a; }
        textarea:focus { border-color: #0070f3; box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.15); }
        .btn { width: 100%; padding: 14px; background-color: #0070f3; color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 14px; box-shadow: 0 4px 14px rgba(0, 112, 243, 0.25); transition: all 0.2s ease; }
        .btn:hover { background-color: #005bb5; transform: translateY(-1px); }
        .btn-copy { background-color: #0070f3; margin-top: 8px; }
        .output-container { margin-top: 24px; display: none; }
        .loader-box { background: #f0f7ff; border: 1px solid #0070f3; border-radius: 12px; padding: 18px; margin-bottom: 16px; }
        .password-box { background: #fffbe3; border: 1px solid #f59e0b; border-radius: 12px; padding: 18px; margin-bottom: 16px; }
        .password-text { font-family: "Fira Code", monospace, sans-serif; font-size: 13px; color: #b45309; word-break: break-all; font-weight: 700; background: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #fde68a; margin-top: 6px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header-bar">
            <h1>Classicfuscator</h1>
        </div>

        <div class="form-group">
            <span class="section-label">Paste Lua Code:</span>
            <textarea id="input" placeholder="print('Hello World!')"></textarea>
        </div>

        <button class="btn" id="obfuscateBtn" onclick="obfuscate()">Obfuscate & Generate Loader</button>

        <div class="output-container" id="outputWrapper">
            <div class="password-box">
                <span class="section-label" style="color: #b45309; font-weight: 700;">🔑 Owner Password (45 Characters):</span>
                <div class="password-text" id="passwordOutput">-- Password will appear here</div>
                <button class="btn" style="background-color: #d97706; margin-top: 10px;" onclick="copyPassword()">Copy Password</button>
            </div>

            <div class="loader-box">
                <span class="section-label" style="color: #0070f3; font-weight: 700;">🚀 Roblox Loader Script:</span>
                <textarea id="loaderOutput" style="height: 70px;" readonly></textarea>
                <button class="btn btn-copy" onclick="copyLoader()">Copy Roblox Loader</button>
            </div>
        </div>
    </div>

    <script>
        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const loaderArea = document.getElementById('loaderOutput');
            const passwordArea = document.getElementById('passwordOutput');
            
            outputWrapper.style.display = "block";
            loaderArea.value = "-- Obfuscating & generating loader, please wait...";
            passwordArea.innerText = "...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                loaderArea.value = data.loader || "-- Error generating loader.";
                passwordArea.innerText = data.password || "N/A";
            } catch (err) {
                loaderArea.value = "-- Loader generation failed: " + err;
            }
        }

        function copyLoader() {
            const loaderArea = document.getElementById('loaderOutput');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            alert('Roblox Loader copied to clipboard!');
        }

        function copyPassword() {
            const passText = document.getElementById('passwordOutput').innerText;
            navigator.clipboard.writeText(passText);
            alert('Owner Password copied to clipboard!');
        }
    </script>
</body>
</html>
"""

# Light Theme Password Prompt for Web Browsers
PASSWORD_PROMPT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Protected Endpoint - Classicfuscator</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #f0f7ff; color: #1e293b; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 12px 40px rgba(0, 112, 243, 0.08); width: 100%; max-width: 480px; padding: 36px; border: 1px solid #e2e8f0; text-align: center; }
        h1 { font-size: 22px; font-weight: 800; color: #0070f3; margin: 0 0 10px 0; }
        p { font-size: 14px; color: #475569; margin-bottom: 20px; }
        input[type="password"] { width: 100%; padding: 14px; border: 1px solid #cbd5e1; border-radius: 10px; font-family: monospace; font-size: 14px; outline: none; background-color: #ffffff; color: #0f172a; margin-bottom: 14px; text-align: center; }
        input[type="password"]:focus { border-color: #0070f3; box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.15); }
        .btn { width: 100%; padding: 14px; background-color: #0070f3; color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; transition: all 0.2s ease; }
        .btn:hover { background-color: #005bb5; }
        .error { color: #e11d48; font-size: 13px; margin-top: 12px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔒 Owner Authentication</h1>
        <p>This script endpoint is protected. Enter your 45-character Owner Password to view the code.</p>

        <form method="POST" action="/raw/{{ token }}">
            <input type="password" name="password" placeholder="Enter 45-character key..." required autocomplete="off">
            <button type="submit" class="btn">View Source Code</button>
        </form>

        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
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
    
    token = uuid.uuid4().hex
    password = generate_password(45)
    
    # Store in RAM
    SCRIPT_CACHE[token] = {
        "code": obfuscated_code,
        "password": password,
        "created_at": time.time()
    }
    
    # Store on Disk
    file_path = os.path.join(SAVED_DIR, f"{token}.lua")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"-- KEY:{password}\n" + obfuscated_code)
    
    domain_url = request.host_url.rstrip("/")
    if domain_url.startswith("http://") and not ("127.0.0.1" in domain_url or "localhost" in domain_url):
        domain_url = domain_url.replace("http://", "https://", 1)

    loader_script = f'loadstring(game:HttpGet("{domain_url}/raw/{token}"))()'

    return jsonify({
        "loader": loader_script,
        "token": token,
        "password": password
    })


@app.route("/raw/<token>", methods=["GET", "POST"])
def serve_script(token):
    user_agent = request.headers.get("User-Agent", "")

    code = None
    expected_password = None

    if token in SCRIPT_CACHE:
        code = SCRIPT_CACHE[token]["code"]
        expected_password = SCRIPT_CACHE[token]["password"]
    else:
        file_path = os.path.join(SAVED_DIR, f"{token}.lua")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines and lines[0].startswith("-- KEY:"):
                    expected_password = lines[0].replace("-- KEY:", "").strip()
                    code = "".join(lines[1:])

    if not code or not expected_password:
        return Response("-- Error 404: Script token not found or expired.", status=404, mimetype="text/plain")

    # Roblox Game Client Request: Returns payload directly to game:HttpGet
    if "Roblox" in user_agent:
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        res.headers["Pragma"] = "no-cache"
        return res

    # Web Browser Request: Requires 45-character password
    submitted_pass = request.form.get("password") or request.args.get("password", "")

    if submitted_pass and submitted_pass.strip() == expected_password:
        res = Response(code, mimetype="text/plain")
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return res

    error_msg = ""
    if submitted_pass:
        error_msg = "❌ Invalid 45-character password. Access denied."

    return render_template_string(PASSWORD_PROMPT_TEMPLATE, token=token, error=error_msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
