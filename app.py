import base64
import random
import re
import string
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)


class HighSecurityLuaObfuscator:
    """Advanced Luau Obfuscation Engine with Multi-Layer Protection."""

    def __init__(self):
        self.used_names = set()

    def generate_ambiguous_identifier(self, length=18):
        """Generates visually ambiguous variable names (Homoglyph technique)."""
        alphabet = "Il1O0"
        while True:
            # Must start with a non-digit valid identifier start
            prefix = random.choice(["I", "l", "_"])
            body = "".join(random.choices(alphabet, k=length - 1))
            name = prefix + body
            if name not in self.used_names:
                self.used_names.add(name)
                return name

    def generate_junk_code(self):
        """Generates realistic-looking opaque predicates and useless operations."""
        v1 = self.generate_ambiguous_identifier(8)
        v2 = self.generate_ambiguous_identifier(8)
        val1 = random.randint(100, 999)
        val2 = random.randint(100, 999)

        junk_patterns = [
            f"local {v1} = ({val1} * {val2}) % {random.randint(10, 50)}; if {v1} == -1 then return end",
            f"local {v1} = math.sin({val1}) + math.cos({val2}); if {v1} == 999 then error() end",
            f"local {v1} = {{{val1}, {val2}}}; local {v2} = {v1}[1] + {v1}[2]",
        ]
        return random.choice(junk_patterns)

    def obfuscate(self, code: str) -> str:
        # Reset identifier tracking per run
        self.used_names.clear()

        # 1. Clean Comments and Whitespace
        code = re.sub(r"--\[\[[\s\S]*?\]\]", "", code)
        code = re.sub(r"--.*$", "", code, flags=re.MULTILINE)

        if not code.strip():
            return "-- [Error]: Empty script provided."

        # 2. Dynamic Key Schedule Generation
        master_key = random.randint(32, 224)
        secondary_key = random.randint(1, 255)
        step_modifier = random.randint(3, 17)

        # 3. Encrypt payload using continuous rolling polyalphabetic key
        encrypted_bytes = []
        raw_bytes = code.encode("utf-8")

        for index, byte in enumerate(raw_bytes):
            dynamic_key = (
                master_key + (index * step_modifier) ^ secondary_key
            ) % 256
            encrypted_byte = byte ^ dynamic_key
            encrypted_bytes.append(encrypted_byte)

        # 4. Split encrypted bytes into multi-chunk lookup tables
        chunk_size = max(16, len(encrypted_bytes) // 4)
        chunks = [
            encrypted_bytes[i : i + chunk_size]
            for i in range(0, len(encrypted_bytes), chunk_size)
        ]

        chunk_vars = []
        chunk_definitions = []
        for chunk in chunks:
            c_var = self.generate_ambiguous_identifier()
            chunk_vars.append(c_var)
            table_str = ",".join(map(str, chunk))
            chunk_definitions.append(f"local {c_var} = {{{table_str}}}")

        # 5. Identifier generation for loader runtime
        v_master_key = self.generate_ambiguous_identifier()
        v_sec_key = self.generate_ambiguous_identifier()
        v_step = self.generate_ambiguous_identifier()
        v_output = self.generate_ambiguous_identifier()
        v_char_func = self.generate_ambiguous_identifier()
        v_index = self.generate_ambiguous_identifier()
        v_byte = self.generate_ambiguous_identifier()
        v_dyn_key = self.generate_ambiguous_identifier()
        v_exec = self.generate_ambiguous_identifier()
        v_anti_dump = self.generate_ambiguous_identifier()
        v_combined = self.generate_ambiguous_identifier()

        # 6. Build High-Security Loader Stub
        stub = f"""
--[[ High-Security Protection Engine v3.0 ]]--
local {v_anti_dump} = setmetatable({{}}, {{
    __index = function(t, k)
        if k == "hooked" then return false end
    end
}})

-- Anti-Constant Dump & Integrity Check
if type(getfenv) ~= "function" or getfenv().hookfunction or hookfunction then
    while true do end
end

{self.generate_junk_code()}

local {v_master_key} = {master_key}
local {v_sec_key} = {secondary_key}
local {v_step} = {step_modifier}
local {v_char_func} = string.char

{chr(10).join(chunk_definitions)}

local {v_combined} = {{}}
{chr(10).join([f"for _, b in ipairs({c}) do table.insert({v_combined}, b) end" for c in chunk_vars])}

{self.generate_junk_code()}

local {v_output} = {{}}
for {v_index} = 1, #{v_combined} do
    local {v_byte} = {v_combined}[{v_index}]
    local {v_dyn_key} = bit32 and bit32.bxor(({v_master_key} + ({v_index} - 1) * {v_step}), {v_sec_key}) % 256 
        or (({v_master_key} + ({v_index} - 1) * {v_step}) + {v_sec_key}) % 256
    
    local d_byte = bit32 and bit32.bxor({v_byte}, {v_dyn_key}) or (({v_byte} - {v_dyn_key}) % 256)
    {v_output}[{v_index}] = {v_char_func}(d_byte)
end

{self.generate_junk_code()}

local {v_exec} = getfenv().loadstring or load
local res, err = {v_exec}(table.concat({v_output}))

if res and type(res) == "function" then
    task.spawn(res)
else
    error("Runtime integrity failure", 0)
end
"""
        return stub.strip()


# Initialize Engine Instance
engine = HighSecurityLuaObfuscator()

# HTML & UI Layout
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Advanced Luau Obfuscator v3</title>
    <style>
        body {
            background-color: #0b0c10;
            color: #c5c6c7;
            font-family: 'Consolas', 'Segoe UI', monospace;
            margin: 0;
            padding: 30px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { color: #66fcf1; margin-bottom: 5px; text-shadow: 0 0 10px rgba(102, 252, 241, 0.3); }
        p { color: #45a29e; margin-bottom: 25px; }
        .container {
            display: flex;
            width: 100%;
            max-width: 1100px;
            gap: 20px;
        }
        .box {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        label { margin-bottom: 8px; color: #66fcf1; font-weight: bold; }
        textarea {
            width: 100%;
            height: 480px;
            background-color: #1f2833;
            border: 1px solid #45a29e;
            border-radius: 6px;
            color: #66fcf1;
            padding: 14px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            resize: none;
            box-sizing: border-box;
        }
        textarea:focus { outline: none; border-color: #66fcf1; box-shadow: 0 0 8px rgba(102, 252, 241, 0.5); }
        button {
            margin-top: 20px;
            padding: 14px 35px;
            background-color: #45a29e;
            color: #0b0c10;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        button:hover { background-color: #66fcf1; box-shadow: 0 0 12px rgba(102, 252, 241, 0.6); }
    </style>
</head>
<body>

    <h1>Advanced Luau Obfuscator v3</h1>
    <p>Multi-layer polyalphabetic encryption & anti-dump integrity control.</p>

    <div class="container">
        <div class="box">
            <label for="input">Source Code (Raw Luau)</label>
            <textarea id="input" placeholder="print('Protected System Loaded')"></textarea>
        </div>
        <div class="box">
            <label for="output">Obfuscated Output</label>
            <textarea id="output" readonly placeholder="Obfuscated stream will appear here..."></textarea>
        </div>
    </div>

    <button onclick="obfuscate()">Protect Script</button>

    <script>
        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputArea = document.getElementById('output');
            
            outputArea.value = "-- Encrypting payload and building dynamic loader...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                if (data.result) {
                    outputArea.value = data.result;
                } else {
                    outputArea.value = "-- Protection Error: Failed to process script.";
                }
            } catch (err) {
                outputArea.value = "-- Communication Error: " + err;
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
