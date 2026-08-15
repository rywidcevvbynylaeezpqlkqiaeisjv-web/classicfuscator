import json
import math
import os
import random
import re
import secrets
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


def generate_password(length=55) -> str:
    """Generates a secure alphanumeric password of specified length."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


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
    <title>Classicfuscator Enterprise - Hardened VM</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #f8fafc; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #1c2541; border-radius: 16px; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5); width: 100%; max-width: 640px; padding: 32px; border: 1px solid #3a506b; }
        h1 { font-size: 24px; font-weight: 800; color: #6fffe9; margin: 0 0 20px 0; }
        .form-group { margin-bottom: 18px; }
        .section-label { font-size: 13px; font-weight: 600; color: #a5a5a5; margin-bottom: 8px; display: block; }
        textarea, input[type="text"] { width: 100%; border: 1px solid #3a506b; border-radius: 10px; padding: 14px; font-family: monospace; font-size: 13px; outline: none; background-color: #0b132b; color: #6fffe9; }
        textarea:focus, input[type="text"]:focus { border-color: #5bc0be; }
        textarea { height: 160px; }
        .btn { width: 100%; padding: 14px; background-color: #5bc0be; color: #0b132b; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 10px; transition: all 0.2s ease; }
        .btn:hover { background-color: #6fffe9; }
        .output-container { margin-top: 24px; display: none; }
        .loader-box { background: #0b132b; border: 1px solid #5bc0be; border-radius: 10px; padding: 16px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🛡️ Classicfuscator Hardened VM</h1>

        <div class="form-group">
            <span class="section-label">Paste Lua / Luau Source:</span>
            <textarea id="input" placeholder="print('Hello World')"></textarea>
        </div>

        <button class="btn" onclick="obfuscate()">Obfuscate & Generate Loader</button>

        <div class="output-container" id="outputWrapper">
            <div class="loader-box">
                <span class="section-label" style="color: #6fffe9;">🚀 Roblox Loader Script:</span>
                <textarea id="loaderOutput" style="height: 70px;" readonly></textarea>
                <button class="btn" style="background-color: #3a506b; color: #ffffff;" onclick="copyLoader()">Copy Loader</button>
            </div>

            <div class="loader-box">
                <span class="section-label" style="color: #ff6b6b;">🔑 Generated Password (55 Characters):</span>
                <input type="text" id="passwordOutput" readonly />
                <button class="btn" style="background-color: #3a506b; color: #ffffff;" onclick="copyPassword()">Copy Password</button>
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
            loaderArea.value = "-- Processing Hardened VM Cipher...";
            passwordArea.value = "Generating...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                loaderArea.value = data.loader || "-- Error generating loader.";
                passwordArea.value = data.password || "";
            } catch (err) {
                loaderArea.value = "-- Generation failed: " + err;
                passwordArea.value = "";
            }
        }

        function copyLoader() {
            const loaderArea = document.getElementById('loaderOutput');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            alert('Loader copied to clipboard!');
        }

        function copyPassword() {
            const passwordArea = document.getElementById('passwordOutput');
            passwordArea.select();
            navigator.clipboard.writeText(passwordArea.value);
            alert('Password copied to clipboard!');
        }
    </script>
</body>
</html>
"""

PASSWORD_GATE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Access Protected Script</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b132b; color: #f8fafc; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #1c2541; border-radius: 16px; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5); width: 100%; max-width: 500px; padding: 32px; border: 1px solid #3a506b; }
        h1 { font-size: 20px; font-weight: 800; color: #6fffe9; margin: 0 0 15px 0; text-align: center; }
        p { font-size: 13px; color: #a5a5a5; text-align: center; margin-bottom: 20px; }
        input[type="password"], input[type="text"] { width: 100%; border: 1px solid #3a506b; border-radius: 10px; padding: 14px; font-family: monospace; font-size: 13px; outline: none; background-color: #0b132b; color: #6fffe9; margin-bottom: 15px; }
        input:focus { border-color: #5bc0be; }
        .btn { width: 100%; padding: 14px; background-color: #5bc0be; color: #0b132b; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; transition: all 0.2s ease; }
        .btn:hover { background-color: #6fffe9; }
        .error { color: #ff6b6b; font-size: 13px; margin-bottom: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <h1>🔒 Protected Script Access</h1>
        <p>Please enter the 55-character password to unlock the obfuscated script.</p>

        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}

        <form method="GET" action="">
            <input type="text" name="password" placeholder="Enter 55-character password..." required maxlength="55" autocomplete="off" />
            <button type="submit" class="btn">Unlock & View Script</button>
        </form>
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
    
    # Dynamic 32-character Hex Token & 55-character Password
    token = uuid.uuid4().hex
    password = generate_password(55)
    
    # Store in RAM Cache
    SCRIPT_CACHE[token] = {
        "code": obfuscated_code,
        "password": password,
        "created_at": time.time()
    }
    
    # Store on Disk
    file_path = os.path.join(SAVED_DIR, f"{token}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"code": obfuscated_code, "password": password}, f)
    
    # Enforce HTTPS URL
    domain_url = request.host_url.rstrip("/")
    if domain_url.startswith("http://") and not ("127.0.0.1" in domain_url or "localhost" in domain_url):
        domain_url = domain_url.replace("http://", "https://", 1)

    loader_script = f'loadstring(game:HttpGet("{domain_url}/raw/{token}?password={password}"))()'

    return jsonify({
        "loader": loader_script,
        "token": token,
        "password": password
    })


@app.route("/raw/<token>", methods=["GET", "POST"])
def serve_script(token):
    """
    Serves payload after validating the 55-character password.
    Displays an interactive password form if accessed in a browser without valid key.
    """
    user_agent = request.headers.get("User-Agent", "")

    # Retrieve script record from cache or disk
    record = SCRIPT_CACHE.get(token)
    if not record:
        file_path = os.path.join(SAVED_DIR, f"{token}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                record = None

    if not record:
        return Response("-- Error 404: Invalid or Expired Token.", status=404, mimetype="text/plain")

    target_password = record.get("password")
    code = record.get("code")

    # Get password attempt from query parameters or form submission
    provided_password = request.args.get("password") or request.form.get("password")

    # If valid password provided, return the raw obfuscated script
    if provided_password and secrets.compare_digest(provided_password, target_password):
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        res.headers["Pragma"] = "no-cache"
        return res

    # If invalid password attempt was made
    error_msg = "Incorrect Password. Access Denied." if provided_password else None

    # Render HTML Password Gate
    return render_template_string(PASSWORD_GATE_TEMPLATE, error=error_msg), 401 if error_msg else 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
