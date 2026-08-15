import math
import os
import random
import re
import sqlite3
import time
import uuid
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

# ==============================================================================
# 1. APPLICATION SETUP & PERSISTENT DATABASE
# ==============================================================================

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Render Custom Domain (Set your render URL here or leave blank to auto-detect)
CUSTOM_DOMAIN = "https://classicfuscator.onrender.com"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR = os.path.join(BASE_DIR, "saved_scripts")
DB_PATH = os.path.join(BASE_DIR, "database.db")
os.makedirs(SAVED_DIR, exist_ok=True)

SCRIPT_CACHE = {}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS scripts 
           (token TEXT PRIMARY KEY, code TEXT, created_at REAL)"""
    )
    conn.commit()
    conn.close()

init_db()

def random_id(prefix="v"):
    chars = ["I", "l", "1", "_"]
    body = "".join(random.choices(chars, k=random.randint(18, 26)))
    return f"{prefix}_{body}"


# ==============================================================================
# 2. TOKENIZER & LEXICAL PARSER
# ==============================================================================

TOKEN_SPEC = [
    ("COMMENT_LONG", r"--\[\[[\s\S]*?\]\]|--\[=\[[\s\S]*?\]=\]"),
    ("COMMENT_SHORT", r"--[^\n]*"),
    ("STRING_SQ", r"'([^'\\]|\\.)*'"),
    ("STRING_DQ", r'"([^"\\]|\\.)*"'),
    ("STRING_LONG", r"\[\[[\s\S]*?\]\]"),
    ("NUMBER_HEX", r"0[xX][0-9a-fA-F]+"),
    ("NUMBER_DEC", r"\b\d+\.?\d*(?:[eE][+-]?\d+)?\b"),
    ("OPERATOR", r"==|~=|<=|>=|\.\.|\+|\-|\*|\/|\%|\^|\#|\<|\>|\="),
    ("SYMBOL", r"[\(\)\[\]\{\}\;\,\.:]"),
    ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("WHITESPACE", r"\s+"),
]
TOKEN_REGEX = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))

def tokenize_lua(code: str):
    tokens = []
    for match in TOKEN_REGEX.finditer(code):
        kind = match.lastgroup
        val = match.group()
        if kind != "WHITESPACE" and not kind.startswith("COMMENT"):
            tokens.append((kind, val))
    return tokens


# ==============================================================================
# 3. BYTECODE COMPILER & VIRTUAL INSTRUCTION ENGINE
# ==============================================================================

OPCODES = [
    "OP_LOADK",
    "OP_LOADBOOL",
    "OP_LOADNIL",
    "OP_GETGLOBAL",
    "OP_SETGLOBAL",
    "OP_GETTABLE",
    "OP_SETTABLE",
    "OP_MOVE",
    "OP_CALL",
    "OP_ADD",
    "OP_SUB",
    "OP_MUL",
    "OP_DIV",
    "OP_CONCAT",
    "OP_RETURN",
]

class VMCompiler:
    def __init__(self):
        shuffled = list(OPCODES)
        random.shuffle(shuffled)
        self.isa = {op: idx + 1 for idx, op in enumerate(shuffled)}
        self.constants = []
        self.instructions = []
        self.locals_map = {}
        self.reg_top = 0

    def get_const(self, val):
        if val in self.constants:
            return self.constants.index(val)
        self.constants.append(val)
        return len(self.constants) - 1

    def emit(self, op_name, a=0, b=0, c=0):
        op_code = self.isa[op_name]
        self.instructions.append((op_code, a, b, c))
        return len(self.instructions) - 1

    def alloc_reg(self):
        r = self.reg_top
        self.reg_top += 1
        return r

    def parse_primary_expression(self, tokens, start_idx):
        idx = start_idx
        kind, val = tokens[idx]
        reg = self.alloc_reg()

        if kind in ("STRING_SQ", "STRING_DQ"):
            s_val = val[1:-1]
            k_idx = self.get_const(s_val)
            self.emit("OP_LOADK", reg, k_idx, 0)
            idx += 1
        elif kind == "STRING_LONG":
            s_val = re.sub(r"^\[=*\[|\]=*\]$", "", val)
            k_idx = self.get_const(s_val)
            self.emit("OP_LOADK", reg, k_idx, 0)
            idx += 1
        elif kind in ("NUMBER_DEC", "NUMBER_HEX"):
            n_val = int(val, 16) if val.startswith("0x") else (float(val) if "." in val else int(val))
            k_idx = self.get_const(n_val)
            self.emit("OP_LOADK", reg, k_idx, 0)
            idx += 1
        elif kind == "IDENTIFIER":
            if val == "true":
                self.emit("OP_LOADBOOL", reg, 1, 0)
                idx += 1
            elif val == "false":
                self.emit("OP_LOADBOOL", reg, 0, 0)
                idx += 1
            elif val == "nil":
                self.emit("OP_LOADNIL", reg, 0, 0)
                idx += 1
            elif val in self.locals_map:
                self.emit("OP_MOVE", reg, self.locals_map[val], 0)
                idx += 1
            else:
                k_idx = self.get_const(val)
                self.emit("OP_GETGLOBAL", reg, k_idx, 0)
                idx += 1
        else:
            self.emit("OP_LOADNIL", reg, 0, 0)
            idx += 1

        # Handle member access like game.Workspace or obj:Method
        while idx < len(tokens) and tokens[idx][1] in (".", ":"):
            sep = tokens[idx][1]
            idx += 1
            if idx < len(tokens) and tokens[idx][0] == "IDENTIFIER":
                member_name = tokens[idx][1]
                k_idx = self.get_const(member_name)
                next_reg = self.alloc_reg()
                self.emit("OP_GETTABLE", next_reg, reg, k_idx)
                reg = next_reg
                idx += 1

        return reg, idx

    def parse_expression(self, tokens, start_idx):
        reg, idx = self.parse_primary_expression(tokens, start_idx)

        # Handle binary operators
        if idx < len(tokens) and tokens[idx][0] == "OPERATOR" and tokens[idx][1] != "=":
            op_symbol = tokens[idx][1]
            idx += 1
            right_reg, next_idx = self.parse_expression(tokens, idx)
            idx = next_idx

            res_reg = self.alloc_reg()
            if op_symbol == "+": self.emit("OP_ADD", res_reg, reg, right_reg)
            elif op_symbol == "-": self.emit("OP_SUB", res_reg, reg, right_reg)
            elif op_symbol == "*": self.emit("OP_MUL", res_reg, reg, right_reg)
            elif op_symbol == "/": self.emit("OP_DIV", res_reg, reg, right_reg)
            elif op_symbol == "..": self.emit("OP_CONCAT", res_reg, reg, right_reg)
            return res_reg, idx

        return reg, idx

    def compile(self, tokens):
        i = 0
        n = len(tokens)

        while i < n:
            kind, val = tokens[i]

            # local x = expr
            if kind == "IDENTIFIER" and val == "local" and (i + 1) < n and tokens[i + 1][0] == "IDENTIFIER":
                var_name = tokens[i + 1][1]
                i += 2
                if i < n and tokens[i][1] == "=":
                    i += 1
                    reg, next_i = self.parse_expression(tokens, i)
                    self.locals_map[var_name] = reg
                    i = next_i
                continue

            # Variable assignment: x = expr
            elif kind == "IDENTIFIER" and (i + 1) < n and tokens[i + 1][1] == "=":
                var_name = val
                i += 2
                reg, next_i = self.parse_expression(tokens, i)
                if var_name in self.locals_map:
                    self.emit("OP_MOVE", self.locals_map[var_name], reg, 0)
                else:
                    k_idx = self.get_const(var_name)
                    self.emit("OP_SETGLOBAL", reg, k_idx, 0)
                i = next_i
                continue

            # Function Call or Method Invocation
            elif kind == "IDENTIFIER":
                fn_reg, next_i = self.parse_primary_expression(tokens, i)
                i = next_i
                if i < n and tokens[i][1] == "(":
                    i += 1 # skip '('
                    arg_count = 0
                    while i < n and tokens[i][1] != ")":
                        arg_reg, next_arg_i = self.parse_expression(tokens, i)
                        target_reg = fn_reg + 1 + arg_count
                        self.emit("OP_MOVE", target_reg, arg_reg, 0)
                        arg_count += 1
                        i = next_arg_i
                        if i < n and tokens[i][1] == ",":
                            i += 1

                    if i < n and tokens[i][1] == ")":
                        i += 1

                    self.emit("OP_CALL", fn_reg, arg_count + 1, 1)
                continue

            elif val == ";":
                i += 1
                continue
            else:
                i += 1

        self.emit("OP_RETURN", 0, 1, 0)


# ==============================================================================
# 4. RUNTIME LUA VM CODE GENERATOR
# ==============================================================================

def generate_lua_vm(compiler: VMCompiler, settings: dict) -> str:
    xor_key = random.randint(32, 220)

    enc_constants = []
    for c in compiler.constants:
        if isinstance(c, str):
            c_bytes = [(ord(ch) ^ xor_key) for ch in c]
            enc_constants.append(f"{{1,{{{','.join(map(str, c_bytes))}}}}}")
        elif isinstance(c, (int, float)):
            enc_constants.append(f"{{2,{c}}}")
        else:
            enc_constants.append("{0,0}")

    consts_lua = "{" + ",".join(enc_constants) + "}"

    enc_instructions = []
    for inst in compiler.instructions:
        op, a, b, c = inst
        enc_op = (op ^ xor_key) % 256
        enc_a = (a ^ (xor_key + 1)) % 256
        enc_b = (b ^ (xor_key + 2)) % 256
        enc_c = (c ^ (xor_key + 3)) % 256
        enc_instructions.append(f"{{{enc_op},{enc_a},{enc_b},{enc_c}}}")

    instructions_lua = "{" + ",".join(enc_instructions) + "}"

    v_stack = random_id("Stk")
    v_pc = random_id("Pc")
    v_code = random_id("Code")
    v_const = random_id("K")
    v_env = random_id("Env")
    v_bxor = random_id("Bx")
    v_xor_k = random_id("Xk")
    v_inst = random_id("Ins")
    v_op = random_id("Op")
    v_a = random_id("A")
    v_b = random_id("B")
    v_c = random_id("C")

    isa = compiler.isa
    watermark = settings.get("watermark", "").strip()
    watermark_header = f"--[[ {watermark} ]]\n" if watermark else "--[[ Protected by Classicfuscator VM ]]--\n"

    vm_lua = f"""{watermark_header}return (function(...)
    local {v_env} = (getgenv and getgenv()) or _ENV or _G
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

    local {v_xor_k} = {xor_key}
    local raw_k = {consts_lua}
    local {v_code} = {instructions_lua}

    local {v_const} = {{}}
    for i = 1, #raw_k do
        local entry = raw_k[i]
        if entry[1] == 1 then
            local bytes = entry[2]
            local str_buf = {{}}
            for b_idx = 1, #bytes do
                str_buf[b_idx] = string.char({v_bxor}(bytes[b_idx], {v_xor_k}))
            end
            {v_const}[i - 1] = table.concat(str_buf)
        elseif entry[1] == 2 then
            {v_const}[i - 1] = entry[2]
        else
            {v_const}[i - 1] = nil
        end
    end
    raw_k = nil

    local {v_stack} = {{}}
    local {v_pc} = 1

    while {v_pc} <= #{v_code} do
        local {v_inst} = {v_code}[{v_pc}]
        local {v_op} = {v_bxor}({v_inst}[1], {v_xor_k})
        local {v_a}  = {v_bxor}({v_inst}[2], {v_xor_k} + 1)
        local {v_b}  = {v_bxor}({v_inst}[3], {v_xor_k} + 2)
        local {v_c}  = {v_bxor}({v_inst}[4], {v_xor_k} + 3)

        if {v_op} == {isa["OP_LOADK"]} then
            {v_stack}[{v_a}] = {v_const}[{v_b}]
        elseif {v_op} == {isa["OP_LOADBOOL"]} then
            {v_stack}[{v_a}] = ({v_b} ~= 0)
        elseif {v_op} == {isa["OP_LOADNIL"]} then
            {v_stack}[{v_a}] = nil
        elseif {v_op} == {isa["OP_GETGLOBAL"]} then
            {v_stack}[{v_a}] = {v_env}[{v_const}[{v_b}]]
        elseif {v_op} == {isa["OP_SETGLOBAL"]} then
            {v_env}[{v_const}[{v_b}]] = {v_stack}[{v_a}]
        elseif {v_op} == {isa["OP_GETTABLE"]} then
            local obj = {v_stack}[{v_b}]
            local key = {v_const}[{v_c}]
            if obj ~= nil then
                {v_stack}[{v_a}] = obj[key]
            end
        elseif {v_op} == {isa["OP_MOVE"]} then
            {v_stack}[{v_a}] = {v_stack}[{v_b}]
        elseif {v_op} == {isa["OP_ADD"]} then
            {v_stack}[{v_a}] = {v_stack}[{v_b}] + {v_stack}[{v_c}]
        elseif {v_op} == {isa["OP_SUB"]} then
            {v_stack}[{v_a}] = {v_stack}[{v_b}] - {v_stack}[{v_c}]
        elseif {v_op} == {isa["OP_MUL"]} then
            {v_stack}[{v_a}] = {v_stack}[{v_b}] * {v_stack}[{v_c}]
        elseif {v_op} == {isa["OP_DIV"]} then
            {v_stack}[{v_a}] = {v_stack}[{v_b}] / {v_stack}[{v_c}]
        elseif {v_op} == {isa["OP_CONCAT"]} then
            {v_stack}[{v_a}] = tostring({v_stack}[{v_b}]) .. tostring({v_stack}[{v_c}])
        elseif {v_op} == {isa["OP_CALL"]} then
            local fn = {v_stack}[{v_a}]
            local args = {{}}
            local arg_idx = 1
            for k = {v_a} + 1, {v_a} + {v_b} - 1 do
                args[arg_idx] = {v_stack}[k]
                arg_idx = arg_idx + 1
            end
            if type(fn) == "function" then
                fn(unpack(args))
            end
        elseif {v_op} == {isa["OP_RETURN"]} then
            return {v_stack}[{v_a}]
        end

        {v_pc} = {v_pc} + 1
    end
end)(...)"""
    return vm_lua


def compile_pipeline(raw_code: str, settings: dict) -> str:
    tokens = tokenize_lua(raw_code)
    compiler = VMCompiler()
    compiler.compile(tokens)
    return generate_lua_vm(compiler, settings)


# ==============================================================================
# 5. UI DASHBOARD & APIS
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator Enterprise</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #f1f5f9; color: #0f172a; margin: 0; padding: 30px 16px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05); width: 100%; max-width: 600px; padding: 28px; border: 1px solid #e2e8f0; }
        h1 { font-size: 22px; font-weight: 700; margin: 0 0 16px 0; }
        textarea { width: 100%; height: 160px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; font-family: monospace; font-size: 13px; outline: none; }
        textarea:focus { border-color: #2563eb; }
        .btn { width: 100%; padding: 12px; background-color: #2563eb; color: #ffffff; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 10px; }
        .btn:hover { background-color: #1d4ed8; }
        .output-container { margin-top: 18px; display: none; }
        .code-box { margin-bottom: 12px; }
        .box-title { font-size: 12px; font-weight: 700; color: #475569; margin-bottom: 4px; display: block; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator CVM</h1>
        <textarea id="code" placeholder="print('Hello from Obfuscated VM!');"></textarea>
        <button class="btn" id="btn" onclick="runObfuscation()">Obfuscate Script</button>

        <div class="output-container" id="outWrapper">
            <div class="code-box">
                <span class="box-title">Option 1: Direct Full Code (Paste directly into LocalScript):</span>
                <textarea id="directCode" style="height: 110px;" readonly></textarea>
                <button class="btn" style="background:#475569;" onclick="copy('directCode')">Copy Full Obfuscated Code</button>
            </div>

            <div class="code-box">
                <span class="box-title">Option 2: Roblox Executor Loader:</span>
                <textarea id="execLoader" style="height: 48px;" readonly></textarea>
                <button class="btn" style="background:#0284c7;" onclick="copy('execLoader')">Copy Executor Loader</button>
            </div>
        </div>
    </div>

    <script>
        async function runObfuscation() {
            const input = document.getElementById('code').value;
            const outWrapper = document.getElementById('outWrapper');
            if (!input.trim()) return;

            outWrapper.style.display = "block";
            document.getElementById('directCode').value = "-- Compiling VM bytecode...";
            
            try {
                const res = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ code: input })
                });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('directCode').value = data.raw_code;
                    document.getElementById('execLoader').value = data.loader;
                } else {
                    document.getElementById('directCode').value = "-- Error: " + data.error;
                }
            } catch (err) {
                document.getElementById('directCode').value = "-- Server connection error.";
            }
        }

        function copy(id) {
            const el = document.getElementById(id);
            el.select();
            navigator.clipboard.writeText(el.value);
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# 6. ROUTE HANDLERS
# ==============================================================================

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/obfuscate", methods=["POST"])
def obfuscate_endpoint():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code", "")

    if not raw_code.strip():
        return jsonify({"success": False, "error": "Code is empty"}), 400

    token = uuid.uuid4().hex
    try:
        vm_code = compile_pipeline(raw_code, {})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    SCRIPT_CACHE[token] = vm_code

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO scripts (token, code, created_at) VALUES (?, ?, ?)", 
                  (token, vm_code, time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB Save Error:", e)

    if CUSTOM_DOMAIN:
        domain_url = CUSTOM_DOMAIN.rstrip("/")
    else:
        domain_url = request.host_url.rstrip("/")
        if request.headers.get("X-Forwarded-Proto") == "https":
            domain_url = domain_url.replace("http://", "https://", 1)

    loader = f'loadstring(game:HttpGet("{domain_url}/raw/{token}"))()'

    return jsonify({
        "success": True,
        "token": token,
        "raw_code": vm_code,
        "loader": loader
    })

@app.route("/raw/<token>", methods=["GET"])
def serve_raw(token):
    code = SCRIPT_CACHE.get(token)
    if not code:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT code FROM scripts WHERE token = ?", (token,))
            row = c.fetchone()
            if row:
                code = row[0]
                SCRIPT_CACHE[token] = code
            conn.close()
        except Exception:
            pass

    if code:
        res = Response(code, mimetype="text/plain; charset=utf-8")
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Cache-Control"] = "no-cache"
        return res

    return Response("-- [Classicfuscator] Script token not found.", status=404, mimetype="text/plain")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
