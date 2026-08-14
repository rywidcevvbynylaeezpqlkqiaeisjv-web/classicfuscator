import math
import os
import random
import re
import string
import uuid
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# Enable ProxyFix so Flask recognizes HTTPS behind Render/Cloudflare proxies
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Persistent storage folder on server disk
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(BASE_DIR, "saved_scripts")
os.makedirs(SAVED_DIR, exist_ok=True)


def random_id(prefix=""):
    """Generates look-alike confusing variable names."""
    chars = ["I", "l", "1", "_"]
    body = "".join(random.choices(chars, k=random.randint(18, 28)))
    return f"{prefix}_{body}"


def ror(val, count, bits=8):
    """Rotate Right for 8-bit integer."""
    return ((val >> count) | (val << (bits - count))) & 0xFF


def obfuscate_lua(code: str) -> str:
    if not code.strip():
        return "-- Error: Empty script provided."

    # 1. Encryption Keys
    k_seed = random.randint(1000, 999999)
    k_mult = random.randint(3, 19) * 2 + 1
    k_inc = random.randint(1, 255)
    k_shift = random.randint(1, 7)
    k_mask = random.randint(32, 224)

    # 2. Triple-Layer Bitwise Encryption
    raw_bytes = list(code.encode("utf-8"))
    encrypted_bytes = []
    
    current_key = k_seed
    for idx, byte in enumerate(raw_bytes):
        current_key = (current_key * k_mult + k_inc) % 256
        rotated = ror(byte, k_shift)
        enc = (rotated ^ current_key ^ k_mask ^ ((idx + 13) % 256)) % 256
        encrypted_bytes.append(enc)

    # 3. Chunk Array into Dynamic Sub-tables
    chunk_size = random.randint(15, 35)
    chunks = [
        encrypted_bytes[i : i + chunk_size]
        for i in range(0, len(encrypted_bytes), chunk_size)
    ]
    chunks_lua = "{" + ",".join("{" + ",".join(map(str, c)) + "}" for c in chunks) + "}"

    # 4. Identifier Generation
    v_seed = random_id("s")
    v_mult = random_id("m")
    v_inc = random_id("c")
    v_shift = random_id("sh")
    v_mask = random_id("mk")
    v_chunks = random_id("data")
    v_out = random_id("out")
    v_state = random_id("st")
    v_char = random_id("chr")
    v_concat = random_id("cat")
    v_env = random_id("env")
    v_loader = random_id("ld")
    v_res = random_id("res")
    v_err = random_id("err")
    v_idx = random_id("idx")
    v_bxor = random_id("bx")
    v_rol = random_id("rl")
    v_test_fn = random_id("tfn")
    v_test_err = random_id("terr")

    # 5. Corrected Luau Stub
    lua_stub = f"""--[[ Classicfuscator v3 - Persistent Fixed ]]--
return (function(...)
    local {v_seed} = {k_seed}
    local {v_mult} = {k_mult}
    local {v_inc} = {k_inc}
    local {v_shift} = {k_shift}
    local {v_mask} = {k_mask}
    local {v_chunks} = {chunks_lua}

    local {v_env} = (getgenv and getgenv()) or (getfenv and getfenv()) or _ENV or _G
    local {v_loader} = {v_env}.loadstring or load

    -- Smart Anti-Hook Check
    if type({v_loader}) ~= "function" then
        error("[Classicfuscator] Missing loader capability.", 0)
    end

    local {v_test_fn}, {v_test_err} = {v_loader}("return true", "@test")
    if type({v_test_fn}) ~= "function" or {v_test_fn}() ~= true then
        return (function() end)()
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

    local {v_out} = {{}}
    local {v_state} = {v_seed}
    local {v_idx} = 0

    for c_idx = 1, #{v_chunks} do
        local chunk = {v_chunks}[c_idx]
        for b_idx = 1, #chunk do
            {v_state} = ({v_state} * {v_mult} + {v_inc}) % 256
            local raw = chunk[b_idx]
            
            local pos_key = ({v_idx} + 13) % 256
            {v_idx} = {v_idx} + 1
            
            local step1 = {v_bxor}(raw, pos_key)
            local step2 = {v_bxor}(step1, {v_mask})
            local step3 = {v_bxor}(step2, {v_state})
            local unrotated = {v_rol}(step3, {v_shift})
            
            {v_out}[#{v_out} + 1] = {v_char}(unrotated)
        end
    end

    local {v_res}, {v_err} = {v_loader}({v_concat}({v_out}), "@Classicfuscator")

    if type({v_res}) == "function" then
        if setfenv and type({v_env}) == "table" then
            pcall(setfenv, {v_res}, {v_env})
        end
        return {v_res}(...)
    else
        error("[Classicfuscator] Execution Error: " .. tostring({v_err}), 0)
    end
end)(...)"""

    return lua_stub.strip()


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip())
    if not name:
        name = "script_" + str(uuid.uuid4())[:6]
    if not name.endswith(".lua"):
        name += ".lua"
    return name


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator v3</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #f0f7ff; color: #1e293b; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 12px 40px rgba(0, 112, 243, 0.08); width: 100%; max-width: 620px; padding: 36px; border: 1px solid #e2e8f0; position: relative; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        h1 { font-size: 26px; font-weight: 800; color: #0070f3; margin: 0; letter-spacing: -0.5px; }
        .form-group { margin-bottom: 18px; }
        .section-label { font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 8px; display: block; }
        .text-input { width: 100%; padding: 12px 14px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px; outline: none; }
        .text-input:focus { border-color: #0070f3; box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.15); }
        textarea { width: 100%; height: 150px; border: 1px solid #cbd5e1; border-radius: 12px; padding: 14px; font-family: "Fira Code", monospace, sans-serif; font-size: 13px; resize: vertical; outline: none; background-color: #ffffff; color: #0f172a; }
        textarea:focus { border-color: #0070f3; box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.15); }
        .btn { width: 100%; padding: 14px; background-color: #0070f3; color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 14px; box-shadow: 0 4px 14px rgba(0, 112, 243, 0.25); transition: all 0.2s ease; }
        .btn:hover { background-color: #005bb5; transform: translateY(-1px); }
        .btn-copy-loader { background-color: #0070f3; }
        .btn-copy-code { background-color: #10b981; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.25); }
        .btn-copy-code:hover { background-color: #059669; }
        .output-container { margin-top: 24px; display: none; }
        .loader-box { background: #f0f7ff; border: 1px solid #0070f3; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header-bar">
            <h1>Classicfuscator</h1>
        </div>

        <div class="form-group">
            <span class="section-label">Custom Script Name:</span>
            <input type="text" id="filenameInput" class="text-input" placeholder="my_script.lua" value="my_script.lua" onfocus="playSoftTap()">
        </div>

        <div class="form-group">
            <span class="section-label">Paste Lua Code:</span>
            <textarea id="input" placeholder="print('Hello World!')" onfocus="playSoftTap()"></textarea>
        </div>

        <button class="btn" id="obfuscateBtn" onclick="obfuscate()">Obfuscate & Generate Loader</button>

        <div class="output-container" id="outputWrapper">
            <div class="loader-box">
                <span class="section-label" style="color: #0070f3; font-weight: 700;">🚀 Roblox Loader Script:</span>
                <textarea id="loaderOutput" style="height: 60px;" readonly></textarea>
                <button class="btn btn-copy-loader" onclick="copyLoader()">Copy Roblox Loader</button>
            </div>

            <span class="section-label">Full Obfuscated Code:</span>
            <textarea id="output" readonly></textarea>
            <button class="btn btn-copy-code" onclick="copyOutput()">Copy Full Obfuscated Code</button>
        </div>
    </div>

    <script>
        let audioCtx = null;

        function initAudio() {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }

        function playBubblePop() {
            initAudio();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(400, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.04);
            gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.05);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.05);
        }

        function playSoftTap() {
            initAudio();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(120, audioCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(30, audioCtx.currentTime + 0.03);
            gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.03);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start();
            osc.stop(audioCtx.currentTime + 0.03);
        }

        function playAmbientChime() {
            initAudio();
            const freqs = [523.25, 659.25, 783.99, 1046.50];
            freqs.forEach((freq, idx) => {
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, audioCtx.currentTime + (idx * 0.04));
                gain.gain.setValueAtTime(0.05, audioCtx.currentTime + (idx * 0.04));
                gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + (idx * 0.04) + 0.4);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start(audioCtx.currentTime + (idx * 0.04));
                osc.stop(audioCtx.currentTime + (idx * 0.04) + 0.4);
            });
        }

        async function obfuscate() {
            playSoftTap();
            const inputCode = document.getElementById('input').value;
            const filename = document.getElementById('filenameInput').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const outputArea = document.getElementById('output');
            const loaderArea = document.getElementById('loaderOutput');
            
            outputWrapper.style.display = "block";
            outputArea.value = "-- Obfuscating code, please wait...";
            loaderArea.value = "-- Generating loader...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode, filename: filename })
                });

                const data = await response.json();
                outputArea.value = data.result || "-- Error processing script.";
                loaderArea.value = data.loader || "-- Error generating loader.";
                playAmbientChime();
            } catch (err) {
                outputArea.value = "-- Request failed: " + err;
                loaderArea.value = "-- Loader generation failed.";
            }
        }

        function copyLoader() {
            playBubblePop();
            const loaderArea = document.getElementById('loaderOutput');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            alert('Roblox Loader copied to clipboard!');
        }

        function copyOutput() {
            playBubblePop();
            const outputArea = document.getElementById('output');
            outputArea.select();
            navigator.clipboard.writeText(outputArea.value);
            alert('Obfuscated source code copied to clipboard!');
        }
    </script>
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
    raw_filename = data.get("filename", "my_script.lua")
    
    clean_filename = sanitize_filename(raw_filename)
    obfuscated_code = obfuscate_lua(raw_code)
    
    # Save directly to server disk
    file_path = os.path.join(SAVED_DIR, clean_filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(obfuscated_code)
    
    # Enforce HTTPS protocol for Roblox game:HttpGet
    domain_url = request.host_url.rstrip("/")
    if domain_url.startswith("http://") and not ("127.0.0.1" in domain_url or "localhost" in domain_url):
        domain_url = domain_url.replace("http://", "https://", 1)

    loader_script = f'loadstring(game:HttpGet("{domain_url}/{clean_filename}", true))()'

    return jsonify({
        "result": obfuscated_code,
        "loader": loader_script,
        "filename": clean_filename
    })


@app.route("/<filename>", methods=["GET"])
def serve_script(filename):
    file_path = os.path.join(SAVED_DIR, filename)
    
    if not os.path.exists(file_path):
        return Response("-- Error: Script not found on server disk.", status=404, mimetype="text/plain")
    
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
    
    res = Response(code, mimetype="text/plain")
    res.headers["Access-Control-Allow-Origin"] = "*"
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return res


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
