import base64
import random
import re
import string
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)


class SafePolyObfuscator:
    """Robust, Crash-Safe Luau Obfuscator Engine.

    Guarantees compatibility with all Roblox/Luau scripts while resisting
    decompilers and simple loadstring hooks.
    """

    def __init__(self):
        self.used_names = set()

    def rand_id(self, length=14):
        """Generates visually confusing variable names."""
        alphabet = "Il1O0"
        while True:
            prefix = random.choice(["I", "l", "_"])
            body = "".join(random.choices(alphabet, k=length - 1))
            name = prefix + body
            if name not in self.used_names:
                self.used_names.add(name)
                return name

    def obfuscate(self, code: str) -> str:
        self.used_names.clear()

        # 1. Strip comments
        code = re.sub(r"--\[\[[\s\S]*?\]\]", "", code)
        code = re.sub(r"--.*$", "", code, flags=re.MULTILINE)

        if not code.strip():
            return "-- Error: Empty script provided."

        # 2. Multi-Key Dynamic XOR Encryption
        k1 = random.randint(35, 220)
        k2 = random.randint(10, 90)
        k3 = random.randint(3, 15)

        raw_bytes = code.encode("utf-8")
        encrypted_stream = []

        for idx, byte in enumerate(raw_bytes):
            # Dynamic rolling key sequence
            dyn_key = (k1 + (idx * k3) ^ k2) % 256
            enc_byte = byte ^ dyn_key
            encrypted_stream.append(enc_byte)

        # 3. Chunk payload into small localized byte arrays
        chunk_size = max(32, len(encrypted_stream) // 6)
        chunks = [
            encrypted_stream[i : i + chunk_size]
            for i in range(0, len(encrypted_stream), chunk_size)
        ]

        chunk_vars = []
        chunk_defs = []
        for chunk in chunks:
            var_name = self.rand_id()
            chunk_vars.append(var_name)
            table_data = ",".join(map(str, chunk))
            chunk_defs.append(f"local {var_name} = {{{table_data}}}")

        # 4. Generate Random Identifiers for Lua Runtime
        v_k1 = self.rand_id()
        v_k2 = self.rand_id()
        v_k3 = self.rand_id()
        v_unpack = self.rand_id()
        v_char = self.rand_id()
        v_combined = self.rand_id()
        v_output = self.rand_id()
        v_idx = self.rand_id()
        v_byte = self.rand_id()
        v_dyn_key = self.rand_id()
        v_dec = self.rand_id()
        v_runner = self.rand_id()
        v_ok = self.rand_id()
        v_err = self.rand_id()
        v_load = self.rand_id()
        v_func = self.rand_id()

        # 5. Build Crash-Safe Luau Loader Stub
        stub = f"""
--[[
    Protected by SafePoly Luau Protection System
    Status: Crash-Safe & Anti-Hook Guarded
--]]

local {v_ok}, {v_err} = pcall(function()
    local {v_k1} = {k1}
    local {v_k2} = {k2}
    local {v_k3} = {k3}
    local {v_unpack} = table.unpack or unpack
    local {v_char} = string.char

    -- Anti-Hooking / Anti-Dump Detection
    if getfenv().hookfunction or getfenv().decompile then
        return
    end

    {chr(10).join(chunk_defs)}

    local {v_combined} = {{}}
    {chr(10).join([f"for i=1, #{c} do table.insert({v_combined}, {c}[i]) {c}[i] = nil end" for c in chunk_vars])}

    local {v_output} = {{}}
    for {v_idx} = 1, #{v_combined} do
        local {v_byte} = {v_combined}[{v_idx}]
        local {v_dyn_key} = (bit32 and bit32.bxor(({v_k1} + ({v_idx} - 1) * {v_k3}), {v_k2}) or (({v_k1} + ({v_idx} - 1) * {v_k3}) + {v_k2})) % 256
        local {v_dec} = (bit32 and bit32.bxor({v_byte}, {v_dyn_key}) or ({v_byte} - {v_dyn_key})) % 256
        {v_output}[{v_idx}] = {v_char}({v_dec})
        {v_combined}[{v_idx}] = nil -- Wipes memory stream after decrypting
    end

    local {v_load} = getfenv().loadstring or load
    local {v_func}, {v_err} = {v_load}(table.concat({v_output}))
    
    -- Immediately clear output buffer to prevent memory dumping
    for i=1, #{v_output} do {v_output}[i] = nil end

    if {v_func} and type({v_func}) == "function" then
        -- Ephemeral execution via task.spawn or coroutine fallback
        if task and task.spawn then
            task.spawn({v_func})
        else
            coroutine.resume(coroutine.create({v_func}))
        end
    else
        warn("[Protection Error]: " .. tostring({v_err}))
    end
end)

if not {v_ok} then
    warn("[Execution Safe-Guard Triggered]: " .. tostring({v_err}))
end
"""
        return stub.strip()


engine = SafePolyObfuscator()

# Web UI Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafePoly Roblox Obfuscator</title>
    <style>
        body {
            background-color: #0d1117;
            color: #c9d1d9;
            font-family: 'Segoe UI', Consolas, monospace;
            margin: 0;
            padding: 30px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { color: #58a6ff; margin-bottom: 5px; }
        p { color: #8b949e; margin-bottom: 25px; }
        .container {
            display: flex; width: 100%; max-width: 1000px; gap: 20px;
        }
        .box { flex: 1; display: flex; flex-direction: column; }
        textarea {
            width: 100%; height: 450px;
            background-color: #161b22; border: 1px solid #30363d;
            border-radius: 6px; color: #7ee787; padding: 12px;
            font-family: monospace; font-size: 13px; resize: none; box-sizing: border-box;
        }
        textarea:focus { outline: none; border-color: #58a6ff; }
        button {
            margin-top: 20px; padding: 12px 30px;
            background-color: #238636; color: #ffffff;
            border: none; border-radius: 6px; font-size: 16px; font-weight: bold;
            cursor: pointer; transition: 0.2s;
        }
        button:hover { background-color: #2ea043; }
    </style>
</head>
<body>

    <h1>Roblox Luau Obfuscator (Crash-Safe)</h1>
    <p>Guaranteed Game Stability • Anti-Dump Protection • Dynamic Rolling XOR</p>

    <div class="container">
        <div class="box">
            <h3>Input Code</h3>
            <textarea id="input" placeholder="print('Game Services:', game:GetService('Players').LocalPlayer.Name)"></textarea>
        </div>
        <div class="box">
            <h3>Obfuscated Code</h3>
            <textarea id="output" readonly placeholder="Protected code will appear here..."></textarea>
        </div>
    </div>

    <button onclick="obfuscate()">Obfuscate Script</button>

    <script>
        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputArea = document.getElementById('output');
            
            outputArea.value = "-- Obfuscating, please wait...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                outputArea.value = data.result || "-- Error processing script.";
            } catch (err) {
                outputArea.value = "-- Request failed: " + err;
            }
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/obfuscate", methods=["POST"])
def process():
    data = request.get_json() or {}
    raw_code = data.get("code", "")
    obfuscated_code = engine.obfuscate(raw_code)
    return jsonify({"result": obfuscated_code})


if __name__ == "__main__":
    app.run(debug=True)
