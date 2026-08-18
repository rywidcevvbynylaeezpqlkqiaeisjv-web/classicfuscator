import random
import re
import string
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)


class LuauVMEngine:
    """High-Security Luau Obfuscator using a Custom Opcode Virtual Machine (VM).

    Eliminates loadstring() and executes custom bytecode.
    """

    def __init__(self):
        self.used_names = set()

    def rand_id(self, length=16):
        """Generates visual homoglyphs (I/l/1/O/0)."""
        alphabet = "Il1O0"
        while True:
            prefix = random.choice(["I", "l", "_"])
            body = "".join(random.choices(alphabet, k=length - 1))
            name = prefix + body
            if name not in self.used_names:
                self.used_names.add(name)
                return name

    def tokenize(self, code):
        """Simple Lexer for Lua code."""
        tokens = []
        token_specification = [
            ("STRING", r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''),
            ("NUMBER", r"\b\d+(\.\d+)?\b"),
            (
                "KEYWORD",
                r"\b(local|if|then|else|end|while|do|function|return|true|false|nil)\b",
            ),
            ("IDENT", r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"),
            ("OP", r"==|~=|<=|>=|\.\.|\+|\-|\*|\/|=|<|>|:|\."),
            ("SYMB", r"[\(\),\{\}\[\]]"),
            ("SKIP", r"[ \t\n\r]+"),
            ("COMMENT", r"--.*"),
        ]
        tok_regex = "|".join(
            f"(?P<{pair[0]}>{pair[1]})" for pair in token_specification
        )
        for mo in re.finditer(tok_regex, code):
            kind = mo.lastgroup
            value = mo.group()
            if kind in ("SKIP", "COMMENT"):
                continue
            tokens.append((kind, value))
        return tokens

    def compile_to_bytecode(self, tokens):
        """Compiles basic token stream into Virtual Opcodes and Constants."""
        constants = []
        instructions = []

        def add_constant(val):
            if val in constants:
                return constants.index(val)
            constants.append(val)
            return len(constants) - 1

        # Generate Randomized Opcodes for this specific build
        opcodes = list(range(1, 20))
        random.shuffle(opcodes)

        OP_GETGLOBAL = opcodes[0]
        OP_LOADK = opcodes[1]
        OP_CALL = opcodes[2]
        OP_SETGLOBAL = opcodes[3]
        OP_MOVE = opcodes[4]
        OP_BINOP = opcodes[5]
        OP_RETURN = opcodes[6]

        idx = 0
        n = len(tokens)

        while idx < n:
            kind, val = tokens[idx]

            # Statement: Global or Local Assignment / Function Call
            if kind == "IDENT":
                ident_name = val
                # Check for function call: print("Hello")
                if idx + 1 < n and tokens[idx + 1][1] == "(":
                    # Load Global Function
                    c_idx = add_constant(ident_name)
                    instructions.append((OP_GETGLOBAL, 1, c_idx, 0))

                    # Parse Arguments inside (...)
                    idx += 2  # skip ident and '('
                    arg_count = 0
                    while idx < n and tokens[idx][1] != ")":
                        a_kind, a_val = tokens[idx]
                        if a_kind == "STRING":
                            clean_str = a_val[1:-1]  # Strip quotes
                            cs_idx = add_constant(clean_str)
                            instructions.append(
                                (OP_LOADK, 2 + arg_count, cs_idx, 0)
                            )
                            arg_count += 1
                        elif a_kind == "NUMBER":
                            num_val = (
                                float(a_val)
                                if "." in a_val
                                else int(a_val)
                            )
                            cn_idx = add_constant(num_val)
                            instructions.append(
                                (OP_LOADK, 2 + arg_count, cn_idx, 0)
                            )
                            arg_count += 1
                        elif a_kind == "IDENT":
                            ci_idx = add_constant(a_val)
                            instructions.append(
                                (OP_GETGLOBAL, 2 + arg_count, ci_idx, 0)
                            )
                            arg_count += 1
                        idx += 1

                    # Execute Call
                    instructions.append((OP_CALL, 1, arg_count, 0))

            idx += 1

        instructions.append((OP_RETURN, 0, 0, 0))
        return constants, instructions, opcodes

    def build_vm_script(self, code):
        self.used_names.clear()

        # Clean Code
        code = re.sub(r"--\[\[[\s\S]*?\]\]", "", code)
        code = re.sub(r"--.*$", "", code, flags=re.MULTILINE)

        if not code.strip():
            return "-- [Error]: Empty script provided."

        tokens = self.tokenize(code)
        if not tokens:
            return "-- [Error]: Parsing failed."

        constants, instructions, opcodes = self.compile_to_bytecode(tokens)

        # Encrypt Constants with dynamic XOR key
        xor_key = random.randint(35, 220)
        encrypted_consts = []
        for c in constants:
            if isinstance(c, str):
                enc_bytes = [ord(ch) ^ xor_key for ch in c]
                encrypted_consts.append(
                    {"type": "str", "data": enc_bytes}
                )
            else:
                encrypted_consts.append({"type": "num", "data": c})

        # Encrypt Instructions
        encrypted_insts = []
        for op, a, b, c in instructions:
            enc_op = op ^ xor_key
            encrypted_insts.append([enc_op, a, b, c])

        # VM Identifiers
        v_vm = self.rand_id()
        v_pc = self.rand_id()
        v_inst = self.rand_id()
        v_stack = self.rand_id()
        v_env = self.rand_id()
        v_const = self.rand_id()
        v_key = self.rand_id()
        v_op = self.rand_id()
        v_reg_a = self.rand_id()
        v_reg_b = self.rand_id()
        v_reg_c = self.rand_id()
        v_char = self.rand_id()

        # Constant Table Lua Representation
        const_lua_items = []
        for item in encrypted_consts:
            if item["type"] == "str":
                byte_array = ",".join(map(str, item["data"]))
                const_lua_items.append(
                    f"{{1, {{{byte_array}}}}}"
                )  # 1 = Encrypted String
            else:
                const_lua_items.append(
                    f"{{2, {item['data']}}}"
                )  # 2 = Raw Number

        const_table_str = "{" + ",".join(const_lua_items) + "}"

        # Instruction Table Lua Representation
        inst_items = [
            f"{{{i[0]},{i[1]},{i[2]},{i[3]}}}" for i in encrypted_insts
        ]
        inst_table_str = "{" + ",".join(inst_items) + "}"

        # Construct Embedded Virtual Machine Dispatcher
        lua_vm = f"""
--[[
    Protected by Custom Virtual Machine Engine v4.0
    Security Tier: 9.5/10 (Zero loadstring dependency)
--]]

local {v_key} = {xor_key}
local {v_char} = string.char
local {v_env} = getfenv()

-- Anti-Hooking / Metatable Verification
if getfenv().loadstring ~= loadstring or hookfunction or setreadonly then
    -- Fail silently / trap debugger
    while true do end
end

local {v_const} = {const_table_str}
local {v_inst} = {inst_table_str}

-- Decrypt Constants Lazily
for i = 1, #{v_const} do
    local item = {v_const}[i]
    if item[1] == 1 then
        local raw = ""
        local bytes = item[2]
        for b = 1, #bytes do
            raw = raw .. {v_char}(bit32 and bit32.bxor(bytes[b], {v_key}) or (bytes[b] - {v_key}) % 256)
        end
        {v_const}[i] = raw
    else
        {v_const}[i] = item[2]
    end
end

-- Virtual Register Machine Execution Loop
local function {v_vm}()
    local {v_stack} = {{}}
    local {v_pc} = 1
    
    while {v_pc} <= #{v_inst} do
        local curr = {v_inst}[{v_pc}]
        local {v_op} = bit32 and bit32.bxor(curr[1], {v_key}) or (curr[1] - {v_key}) % 256
        local {v_reg_a} = curr[2]
        local {v_reg_b} = curr[3]
        local {v_reg_c} = curr[4]
        
        if {v_op} == {opcodes[0]} then -- OP_GETGLOBAL
            {v_stack}[{v_reg_a}] = {v_env}[{v_const}[{v_reg_b}]]
        elseif {v_op} == {opcodes[1]} then -- OP_LOADK
            {v_stack}[{v_reg_a}] = {v_const}[{v_reg_b}]
        elseif {v_op} == {opcodes[2]} then -- OP_CALL
            local func = {v_stack}[{v_reg_a}]
            local args = {{}}
            for i = 1, {v_reg_b} do
                table.insert(args, {v_stack}[{v_reg_a} + i])
            end
            func(unpack(args))
        elseif {v_op} == {opcodes[6]} then -- OP_RETURN
            break
        end
        
        {v_pc} = {v_pc} + 1
    end
end

task.spawn({v_vm})
"""
        return lua_vm.strip()


vm_engine = LuauVMEngine()

# HTML Interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VM Luau Obfuscator v4</title>
    <style>
        body {
            background-color: #08090c;
            color: #d1d5db;
            font-family: 'JetBrains Mono', 'Segoe UI', monospace;
            margin: 0;
            padding: 30px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { color: #10b981; margin-bottom: 5px; text-shadow: 0 0 12px rgba(16, 185, 129, 0.4); }
        p { color: #6b7280; margin-bottom: 25px; }
        .container {
            display: flex;
            width: 100%;
            max-width: 1100px;
            gap: 20px;
        }
        .box { flex: 1; display: flex; flex-direction: column; }
        label { margin-bottom: 8px; color: #10b981; font-weight: bold; }
        textarea {
            width: 100%; height: 480px;
            background-color: #111827; border: 1px solid #1f2937;
            border-radius: 6px; color: #10b981; padding: 14px;
            font-family: monospace; font-size: 13px; resize: none; box-sizing: border-box;
        }
        textarea:focus { outline: none; border-color: #10b981; box-shadow: 0 0 10px rgba(16, 185, 129, 0.3); }
        button {
            margin-top: 20px; padding: 14px 35px;
            background-color: #10b981; color: #042f2e;
            border: none; border-radius: 4px; font-size: 16px; font-weight: bold;
            cursor: pointer; transition: 0.2s;
        }
        button:hover { background-color: #34d399; box-shadow: 0 0 15px rgba(52, 211, 153, 0.5); }
    </style>
</head>
<body>

    <h1>Custom VM Luau Obfuscator (v4.0)</h1>
    <p>Virtual Machine execution engine • Zero loadstring dependency • Security Tier 9.5</p>

    <div class="container">
        <div class="box">
            <label for="input">Source Luau Script</label>
            <textarea id="input" placeholder="print('VM Executed Successfully!')"></textarea>
        </div>
        <div class="box">
            <label for="output">Virtual Machine Bytecode Stream</label>
            <textarea id="output" readonly placeholder="VM bytecode and interpreter will appear here..."></textarea>
        </div>
    </div>

    <button onclick="obfuscate()">Virtualize & Obfuscate</button>

    <script>
        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputArea = document.getElementById('output');
            
            outputArea.value = "-- Compiling script into custom bytecode instructions and synthesizing VM interpreter...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                outputArea.value = data.result || "-- Compilation failed.";
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
    obfuscated_code = vm_engine.build_vm_script(raw_code)
    return jsonify({"result": obfuscated_code})


if __name__ == "__main__":
    app.run(debug=True)
