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
# 1. APPLICATION & PERSISTENT STORAGE INITIALIZATION
# ==============================================================================

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

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
    chars = ["I", "l", "1", "_", "O", "0"]
    body = "".join(random.choices(chars, k=random.randint(16, 24)))
    return f"{prefix}_{body}"


# ==============================================================================
# 2. LEXER & TOKENIZER
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
    ("SYMBOL", r"[\(\)\[\]\{\}\;\,\.]"),
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
# 3. BYTECODE COMPILER & VIRTUAL INSTRUCTION SET (ISA)
# ==============================================================================

OPCODES = [
    "OP_LOADK",       # R(A) := K(B)
    "OP_LOADBOOL",    # R(A) := (B ~= 0)
    "OP_LOADNIL",     # R(A) := nil
    "OP_GETGLOBAL",   # R(A) := G[K(B)]
    "OP_SETGLOBAL",   # G[K(B)] := R(A)
    "OP_MOVE",        # R(A) := R(B)
    "OP_CALL",        # R(A)(R(A+1), ..., R(A+B-1))
    "OP_ADD",         # R(A) := R(B) + R(C)
    "OP_SUB",         # R(A) := R(B) - R(C)
    "OP_MUL",         # R(A) := R(B) * R(C)
    "OP_DIV",         # R(A) := R(B) / R(C)
    "OP_CONCAT",      # R(A) := R(B) .. R(C)
    "OP_JMP",         # PC := PC + sBx
    "OP_EQ",          # if (R(A) == R(B)) ~= C then PC++
    "OP_LT",          # if (R(A) <  R(B)) ~= C then PC++
    "OP_LE",          # if (R(A) <= R(B)) ~= C then PC++
    "OP_RETURN",      # return R(A), ..., R(A+B-1)
]

class VMCompiler:
    def __init__(self):
        # Dynamic Opcode Permutation per compilation
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

    def parse_expression(self, tokens, start_idx):
        """Parses simple expressions, values, literals, or binary ops."""
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

        # Check for binary operators (+, -, *, .., ==)
        if idx < len(tokens) and tokens[idx][0] == "OPERATOR":
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

            # Parse Variable Assignment: local x = expr OR x = expr
            if kind == "IDENTIFIER" and val == "local" and (i + 1) < n and tokens[i + 1][0] == "IDENTIFIER":
                var_name = tokens[i + 1][1]
                i += 2
                if i < n and tokens[i][1] == "=":
                    i += 1
                    reg, next_i = self.parse_expression(tokens, i)
                    self.locals_map[var_name] = reg
                    i = next_i
                continue

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

            # Parse Function Call: identifier(...)
            elif kind == "IDENTIFIER" and (i + 1) < n and tokens[i + 1][1] == "(":
                func_name = val
                fn_reg = self.alloc_reg()
                
                if func_name in self.locals_map:
                    self.emit("OP_MOVE", fn_reg, self.locals_map[func_name], 0)
                else:
                    k_idx = self.get_const(func_name)
                    self.emit("OP_GETGLOBAL", fn_reg, k_idx, 0)

                i += 2 # Skip '('
                arg_count = 0
                while i < n and tokens[i][1] != ")":
                    arg_reg, next_i = self.parse_expression(tokens, i)
                    target_reg = fn_reg + 1 + arg_count
                    self.emit("OP_MOVE", target_reg, arg_reg, 0)
                    arg_count += 1
                    i = next_i
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
# 4. RUNTIME INTERPRETER GENERATION (NO LOADSTRING)
# ==============================================================================

def generate_lua_vm(compiler: VMCompiler, settings: dict) -> str:
    xor_key = random.randint(32, 220)
    seed = random.randint(10000, 99999)

    # 1. Encrypt Constant Pool
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

    # 2. Encrypt & Flatten Instruction Stream
    enc_instructions = []
    for idx, inst in enumerate(compiler.instructions):
        op, a, b, c = inst
        enc_op = (op ^ xor_key) % 256
        enc_a = (a ^ (xor_key + 1)) % 256
        enc_b = (b ^ (xor_key + 2)) % 256
        enc_c = (c ^ (xor_key + 3)) % 256
        enc_instructions.append(f"{{{enc_op},{enc_a},{enc_b},{enc_c}}}")

    instructions_lua = "{" + ",".join(enc_instructions) + "}"

    # Variable Identifiers
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

    # Anti-Tamper & Environment Safety Block
    anti_hook_block = ""
    if settings.get("antihook", True):
        anti_hook_block = f"""
    local ts = tostring
    if string.find(ts(pcall), "hook") or string.find(ts(string.char), "hook") then
        while true do end
        return
    end
"""

    watermark = settings.get("watermark", "").strip()
    watermark_header = f"--[[ {watermark} ]]\n" if watermark else "--[[ Protected by Classicfuscator VM Architecture ]]--\n"

    isa = compiler.isa

    vm_template = f"""{watermark_header}return (function(...)
    local {v_env} = (getgenv and getgenv()) or _ENV or _G
{anti_hook_block}
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

    -- Constant Pool Realization
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

    -- Register Virtual Machine State
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
            fn(unpack(args))
        elseif {v_op} == {isa["OP_RETURN"]} then
            return {v_stack}[{v_a}]
        end

        {v_pc} = {v_pc} + 1
    end
end)(...)"""
    return vm_template


def compile_pipeline(raw_code: str, settings: dict) -> str:
    tokens = tokenize_lua(raw_code)
    compiler = VMCompiler()
    compiler.compile(tokens)
    return generate_lua_vm(compiler, settings)


# ==============================================================================
# 5. DASHBOARD UI & FLASK ROUTES
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator CVM Enterprise</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #f1f5f9; color: #0f172a; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05); width: 100%; max-width: 580px; padding: 32px; border: 1px solid #e2e8f0; }
        h1 { font-size: 24px; font-weight: 700; margin: 0 0 16px 0; color: #0f172a; }
        .tab-nav { display: flex; gap: 8px; background: #f8fafc; padding: 4px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #e2e8f0; }
        .tab-btn { flex: 1; padding: 10px; border: none; background: transparent; color: #64748b; font-size: 14px; font-weight: 600; border-radius: 8px; cursor: pointer; }
        .tab-btn.active { background: #ffffff; color: #2563eb; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        textarea { width: 100%; height: 180px; border: 1px solid #cbd5e1; border-radius: 10px; padding: 12px; font-family: monospace; font-size: 13px; outline: none; resize: vertical; }
        textarea:focus { border-color: #2563eb; ring: 2px solid #93c5fd; }
        .btn { width: 100%; padding: 12px; background-color: #2563eb; color: #ffffff; border: none; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 14px; }
        .btn:hover { background-color: #1d4ed8; }
        .output-container { margin-top: 20px; display: none; }
        .setting-group { margin-bottom: 14px; background: #f8fafc; padding: 12px 16px; border-radius: 10px; border: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }
        .setting-title { font-size: 13.5px; font-weight: 600; }
        .setting-desc { font-size: 12px; color: #64748b; margin-top: 2px; }
        .switch { position: relative; display: inline-block; width: 40px; height: 22px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; transition: .2s; border-radius: 20px; }
        .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background-color: white; transition: .2s; border-radius: 50%; }
        input:checked + .slider { background-color: #2563eb; }
        input:checked + .slider:before { transform: translateX(18px); }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator CVM</h1>
        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('obfTab', this)">Virtualizer</button>
            <button class="tab-btn" onclick="switchTab('setTab', this)">Settings</button>
        </div>

        <div id="obfTab" class="tab-content active">
            <textarea id="code" placeholder="print('Running via pure register VM architecture');"></textarea>
            <button class="btn" id="btn" onclick="runObfuscation()">Compile to Bytecode VM</button>
            <div class="output-container" id="outWrapper">
                <textarea id="result" style="height: 90px;" readonly></textarea>
                <button class="btn" style="background: #334155; margin-top: 8px;" onclick="copyCode()">Copy Loader</button>
            </div>
        </div>

        <div id="setTab" class="tab-content">
            <div class="setting-group">
                <div>
                    <div class="setting-title">Anti-Tamper & Callstack Integrity</div>
                    <div class="setting-desc">Detects metamethod hijacking and debug hooks.</div>
                </div>
                <label class="switch"><input type="checkbox" id="cfgAntiHook" checked><span class="slider"></span></label>
            </div>
            <div class="setting-group" style="flex-direction: column; align-items: flex-start; gap: 6px;">
                <div class="setting-title">Watermark / Header Note</div>
                <input type="text" id="cfgWatermark" style="width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px;" placeholder="Protected by CVM Engine">
            </div>
        </div>
    </div>

    <script>
        function switchTab(id, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            btn.classList.add('active');
        }

        async function runObfuscation() {
            const input = document.getElementById('code').value;
            const outWrapper = document.getElementById('outWrapper');
            const result = document.getElementById('result');
            if (!input.trim()) return;

            result.value = "-- Virtualizing bytecode instruction blocks...";
            outWrapper.style.display = "block";

            try {
                const res = await fetch('/obfuscate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        code: input,
                        settings: {
                            antihook: document.getElementById('cfgAntiHook').checked,
                            watermark: document.getElementById('cfgWatermark').value
                        }
                    })
                });
                const data = await res.json();
                result.value = data.loader || "-- Compilation Error.";
            } catch (err) {
                result.value = "-- Server Connection Error.";
            }
        }

        function copyCode() {
            const result = document.getElementById('result');
            result.select();
            navigator.clipboard.writeText(result.value);
        }
    </script>
</body>
</html>
"""

PROTECTED_HTML = """<!DOCTYPE html>
<html>
<head><title>Protected Endpoint</title><style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#f8fafc;color:#334155;}</style></head>
<body><div><h3>Classicfuscator Secure Endpoint</h3><p>Direct browser navigation is blocked.</p></div></body>
</html>"""


# ==============================================================================
# 6. ROUTING & RUNTIME ENDPOINTS
# ==============================================================================

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/obfuscate", methods=["POST"])
def obfuscate_endpoint():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code", "")
    settings = data.get("settings", {})

    if not raw_code.strip():
        return jsonify({"success": False, "error": "Input code is empty."}), 400

    token = uuid.uuid4().hex
    try:
        vm_protected_code = compile_pipeline(raw_code, settings)
    except Exception as e:
        return jsonify({"success": False, "error": f"Bytecode Compilation Error: {str(e)}"}), 500

    SCRIPT_CACHE[token] = vm_protected_code
    
    # Save to SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO scripts (token, code, created_at) VALUES (?, ?, ?)", 
                  (token, vm_protected_code, time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        print("Database Save Warning:", e)

    domain_url = request.host_url.rstrip("/")
    if request.headers.get("X-Forwarded-Proto") == "https":
        domain_url = domain_url.replace("http://", "https://", 1)

    loader = f'loadstring(game:HttpGet("{domain_url}/raw/{token}"))()'
    return jsonify({"success": True, "loader": loader, "token": token})


@app.route("/raw/<token>", methods=["GET"])
def serve_raw(token):
    # Differentiate browser visits from HTTP clients / Roblox executors
    if request.headers.get("Sec-Fetch-Dest") == "document" and request.headers.get("Sec-Ch-Ua"):
        return render_template_string(PROTECTED_HTML)

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
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return res

    return Response("-- [Classicfuscator] Script token not found.", status=404, mimetype="text/plain")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
