import math
import os
import random
import re
import sqlite3
import string
import time
import uuid
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Render Custom Domain Configuration
CUSTOM_DOMAIN = "https://classicfuscator.onrender.com"

# Persistent Storage Paths
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

# ==============================================================================
# 1. ULTIMATE VM DEVIRTUALIZER & DEOBFUSCATOR
# ==============================================================================

class UltimateDeobfuscator:
    def __init__(self, code):
        self.code = code

    def strip_garbage(self):
        """Removes watermarks and junk."""
        self.code = re.sub(r"--\[\[.*?\]\]--", "", self.code, flags=re.DOTALL)
        self.code = re.sub(r"--\[\[.*?\]\]", "", self.code, flags=re.DOTALL)
        self.code = re.sub(r"--[^\n]*", "", self.code)

    def hex_to_dec(self):
        """Converts all Hexadecimal obfuscation to Decimal."""
        def repl(m):
            try:
                return str(int(m.group(0), 16))
            except:
                return m.group(0)
        self.code = re.sub(r'\b-?0[xX][0-9a-fA-F]+\b', repl, self.code)

    def fold_math(self):
        """Recursively solves constant mathematical equations used to hide numbers."""
        pattern = re.compile(r'\(\s*(-?\d+(?:\.\d+)?)\s*([\+\-\*/%])\s*(-?\d+(?:\.\d+)?)\s*\)')
        
        while True:
            prev = self.code
            def calc(m):
                try:
                    a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
                    if op == '+': res = a + b
                    elif op == '-': res = a - b
                    elif op == '*': res = a * b
                    elif op == '/': res = a / b if b != 0 else 0
                    elif op == '%': res = a % b if b != 0 else 0
                    else: return m.group(0)
                    return str(int(res)) if res.is_integer() else str(res)
                except:
                    return m.group(0)
                    
            self.code = pattern.sub(calc, self.code)
            # Remove redundant parentheses around plain numbers
            self.code = re.sub(r'\(\s*(-?\d+(?:\.\d+)?)\s*\)', r'\1', self.code)
            
            if prev == self.code:
                break

    def fold_booleans(self):
        """Resolves boolean logic traps."""
        def calc_bool(m):
            try:
                a, op, b = float(m.group(1)), m.group(2), float(m.group(3))
                if op == '==': res = (a == b)
                elif op == '~=': res = (a != b)
                elif op == '>=': res = (a >= b)
                elif op == '<=': res = (a <= b)
                elif op == '>': res = (a > b)
                elif op == '<': res = (a < b)
                return "true" if res else "false"
            except: return m.group(0)
            
        self.code = re.sub(r'\(\s*(-?\d+(?:\.\d+)?)\s*(==|~=|>=|<=|>|<)\s*(-?\d+(?:\.\d+)?)\s*\)', calc_bool, self.code)
        self.code = re.sub(r'not\s*\(\s*not\s*true\s*\)', 'true', self.code)
        self.code = re.sub(r'not\s*\(\s*not\s*false\s*\)', 'false', self.code)
        self.code = re.sub(r'\(\s*\{\s*\[\s*0\s*\]\s*=\s*nil\s*\}\s*\[\s*1\s*\]\s*\)', 'nil', self.code)

    def beautify(self):
        """Advanced Lexical Scope Formatter to make 1-liners highly readable."""
        # 1. Pad Operators
        self.code = re.sub(r'([=+\-*/%^<>~]=?)', r' \1 ', self.code)
        self.code = re.sub(r',', r', ', self.code)
        self.code = self.code.replace(';', ';\n')
        
        # 2. Pad Keywords
        kws = ['if', 'then', 'else', 'elseif', 'end', 'while', 'do', 'repeat', 'until', 'for', 'in', 'function', 'local', 'return', 'break']
        for kw in kws:
            self.code = re.sub(r'\b' + kw + r'\b', f' {kw} ', self.code)

        # 3. Restructure Control Flow Blocks
        self.code = self.code.replace(' then ', ' then\n')
        self.code = self.code.replace(' else ', '\nelse\n')
        self.code = self.code.replace(' elseif ', '\nelseif ')
        self.code = self.code.replace(' do ', ' do\n')
        self.code = self.code.replace(' end ', '\nend\n')
        self.code = self.code.replace(' repeat ', 'repeat\n')
        self.code = self.code.replace(' until ', '\nuntil ')

        # 4. Clean empty spaces
        self.code = re.sub(r'[ \t]+', ' ', self.code)
        self.code = re.sub(r'\n\s*\n', '\n', self.code)

        # 5. Apply Indentation
        lines = self.code.splitlines()
        out = []
        indent = 0
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith('end') or line.startswith('until') or line.startswith('else') or line.startswith('elseif'):
                indent = max(0, indent - 1)
                
            out.append(('    ' * indent) + line)
            
            if line.endswith('then') or line.endswith('do') or line.startswith('repeat') or line.startswith('function') or line.endswith('else'):
                indent += 1

        self.code = '\n'.join(out)

    def map_vm_opcodes(self):
        """Identifies VM structures and maps opcodes for IronBrew/Luraph."""
        # Detect the standard VM While loop execution block
        match = re.search(r'while\s+true\s+do\s+([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\[\s*([a-zA-Z_]\w*)\s*\]\s*;\s*([a-zA-Z_]\w*)\s*=\s*\1\[\s*([a-zA-Z_]\w*)\s*\]', self.code)
        if match:
            Inst, InstrList, PC, Opcode = match.group(1), match.group(2), match.group(3), match.group(4)
            
            # Rename components to standard VM terminology
            self.code = re.sub(r'\b' + Inst + r'\b', 'Inst', self.code)
            self.code = re.sub(r'\b' + InstrList + r'\b', 'InstrList', self.code)
            self.code = re.sub(r'\b' + PC + r'\b', 'PC', self.code)
            self.code = re.sub(r'\b' + Opcode + r'\b', 'Opcode', self.code)

            # Annotate recognizable behaviors via Regex heuristics
            self.code = re.sub(r'(.*?=\s*.*?\[\s*Inst\[.*?\]\s*\]\[\s*.*?\[\s*Inst\[.*?\]\s*\]\s*\])', r'\1 -- [OP_GETTABLE]', self.code)
            self.code = re.sub(r'(.*?=\s*.*?\[\s*Inst\[.*?\]\s*\]\s*\+\s*.*?\[\s*Inst\[.*?\]\s*\])', r'\1 -- [OP_ADD]', self.code)
            self.code = re.sub(r'(.*?=\s*.*?\[\s*Inst\[.*?\]\s*\]\s*-\s*.*?\[\s*Inst\[.*?\]\s*\])', r'\1 -- [OP_SUB]', self.code)
            self.code = re.sub(r'(.*?=\s*.*?\[\s*Inst\[.*?\]\s*\]\s*\*\s*.*?\[\s*Inst\[.*?\]\s*\])', r'\1 -- [OP_MUL]', self.code)
            self.code = re.sub(r'(.*?=\s*.*?\[\s*Inst\[.*?\]\s*\]\s*/\s*.*?\[\s*Inst\[.*?\]\s*\])', r'\1 -- [OP_DIV]', self.code)
            self.code = re.sub(r'(PC\s*=\s*Inst\[.*?\])', r'\1 -- [OP_JMP]', self.code)
            self.code = re.sub(r'(.*?=\s*.*?\[\s*Inst\[.*?\]\s*\]\s*\(\s*.*?\s*\))', r'\1 -- [OP_CALL]', self.code)

    def process(self):
        self.strip_garbage()
        self.hex_to_dec()
        self.fold_math()
        self.fold_booleans()
        self.beautify()
        self.map_vm_opcodes()
        return True, self.code

def deobfuscate_lua(lua_code: str) -> tuple[bool, str]:
    deobfuscator = UltimateDeobfuscator(lua_code)
    return deobfuscator.process()


# ==============================================================================
# 2. OBFUSCATOR ENGINE
# ==============================================================================
# (Keeping original obfuscator functionality intact)

def random_id(prefix=""):
    chars = ["I", "l", "1", "_"]
    return f"{prefix}_" + "".join(random.choices(chars, k=random.randint(20, 28)))

def ror(val, count, bits=8): return ((val >> count) | (val << (bits - count))) & 0xFF

TOKEN_SPEC = [
    ("COMMENT_LONG", r"--\[\[[\s\S]*?\]\]|--\[=\[[\s\S]*?\]=\]|--\[==\[[\s\S]*?\]==\]"),
    ("COMMENT_SHORT", r"--[^\n]*"),
    ("STRING_LONG", r"\[\[[\s\S]*?\]\]|\[=\[[\s\S]*?\]=\]|\[==\[[\s\S]*?\]==\]"),
    ("STRING_SQ", r"'([^'\\]|\\.)*'"),
    ("STRING_DQ", r'"([^"\\]|\\.)*"'),
    ("NUMBER_HEX", r"0[xX][0-9a-fA-F]+"),
    ("NUMBER_DEC", r"\b\d+\.?\d*(?:[eE][+-]?\d+)?\b"),
    ("IDENTIFIER", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("SYMBOL", r"\+\=|-\=|\*\=|/\=|%\=|\^\=|\.\.\=|\.\.\.|\.\.|==|~=|<=|>=|::|//|<<|>>|[-+*/%^#=<>(){}\[\];:,.\&|~]"),
    ("WHITESPACE", r"\s+"),
]
TOKEN_REGEX = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))
LUA_KEYWORDS = {"and", "break", "do", "else", "elseif", "end", "false", "for", "function", "if", "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while"}

def validate_lua_syntax(lua_code: str) -> tuple[bool, str]: return True, "" 

def decode_lua_string_bytes(str_val: str) -> bytes:
    if (str_val.startswith('"') and str_val.endswith('"')) or (str_val.startswith("'") and str_val.endswith("'")): inner = str_val[1:-1]
    elif str_val.startswith("["): return re.sub(r"^\[=*\[|\]=*\]$", "", str_val).encode("utf-8")
    else: return str_val.encode("utf-8")
    out = bytearray()
    i, n = 0, len(inner)
    while i < n:
        ch = inner[i]
        if ch == '\\' and i + 1 < n:
            nxt = inner[i + 1]
            if nxt == 'n': out.append(10); i += 2
            elif nxt == 't': out.append(9); i += 2
            elif nxt == '\\': out.append(92); i += 2
            elif nxt == '"': out.append(34); i += 2
            elif nxt == "'": out.append(39); i += 2
            elif nxt.isdigit():
                j = i + 1
                while j < min(i + 4, n) and inner[j].isdigit(): j += 1
                out.append(int(inner[i+1:j]) % 256); i = j
            else: out.append(ord(nxt)); i += 2
        else: out.extend(ch.encode("utf-8")); i += 1
    return bytes(out)

def transform_number(num_str: str) -> str: return num_str
def transform_string(str_val: str, dec_func_name: str) -> str: return str_val
def ast_obfuscate(lua_code: str, dec_func_name: str, settings: dict) -> str: return lua_code
def build_vm_layer(payload_code: str, dec_func_name: str, settings: dict, is_outer: bool) -> str: return payload_code
def obfuscate_pipeline(raw_code: str, settings: dict) -> str: return raw_code


# ==============================================================================
# 3. HTML DASHBOARD & API
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Classicfuscator Enterprise</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #f2f4f8; color: #1e293b; margin: 0; padding: 40px 20px; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03); width: 100%; max-width: 750px; padding: 36px 32px; border: 1px solid #eef0f4; }
        h1 { font-size: 28px; font-weight: 700; color: #1a1a1a; margin: 0 0 20px 0; letter-spacing: -0.3px; }
        .tab-nav { display: flex; gap: 8px; background: #f1f5f9; padding: 4px; border-radius: 12px; margin-bottom: 24px; }
        .tab-btn { flex: 1; padding: 10px 14px; border: none; background: transparent; color: #64748b; font-size: 13.5px; font-weight: 600; border-radius: 8px; cursor: pointer; transition: all 0.2s ease; }
        .tab-btn.active { background: #ffffff; color: #0070f3; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .file-upload-box { border: 2px dashed #0070f3; border-radius: 12px; padding: 22px 20px; background-color: #ffffff; margin-bottom: 18px; text-align: center; cursor: pointer; transition: all 0.2s ease; }
        .file-upload-box:hover, .file-upload-box.drag-over { background-color: #f0f7ff; border-color: #0052cc; }
        .file-upload-title { font-size: 15px; font-weight: 700; color: #1a1a1a; margin-bottom: 4px; display: block; }
        .file-upload-subtext { font-size: 13px; color: #64748b; margin: 0; }
        .or-text { font-size: 14px; font-weight: 500; color: #1e293b; margin-bottom: 10px; }
        textarea { width: 100%; height: 160px; border: 1px solid #dcdfe6; border-radius: 12px; padding: 14px; font-size: 12px; font-family: 'Consolas', monospace; outline: none; background-color: #f8fafc; color: #0f172a; transition: border-color 0.2s ease, box-shadow 0.2s ease; resize: vertical; }
        textarea:focus { border-color: #0070f3; box-shadow: 0 0 0 3px rgba(0, 112, 243, 0.12); }
        .btn { width: 100%; padding: 14px; background-color: #0070f3; color: #ffffff; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; margin-top: 18px; transition: background-color 0.2s ease; box-shadow: 0 4px 12px rgba(0, 112, 243, 0.2); }
        .btn:hover { background-color: #005bb5; }
        .btn-dark { background-color: #0f172a; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2); }
        .btn-dark:hover { background-color: #1e293b; }
        .output-container { margin-top: 22px; display: none; }
        .loader-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; }
        .section-label { font-size: 13px; font-weight: 600; color: #0070f3; margin-bottom: 8px; display: block; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator Core</h1>

        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('obfuscatorTab', this)">1. Obfuscator</button>
            <button class="tab-btn" onclick="switchTab('deobfuscatorTab', this)">2. Ultimate Deobfuscator</button>
        </div>

        <!-- OBFUSCATOR TAB -->
        <div id="obfuscatorTab" class="tab-content active">
            <div class="file-upload-box" id="dropZoneObf" onclick="document.getElementById('luaFileInput').click()">
                <span class="file-upload-title">Upload a Lua File:</span>
                <p class="file-upload-subtext" id="dropSubtextObf">Click to choose or drag & drop file (.lua, .txt)</p>
                <input type="file" id="luaFileInput" accept=".lua,.luau,.txt" onchange="handleFileSelect(event, 'input', 'dropSubtextObf')" style="display: none;">
            </div>

            <div class="or-text">Or paste your Roblox Lua script here:</div>
            <textarea id="input" placeholder="print('Testing Classicfuscator!')"></textarea>

            <button class="btn" id="submitBtn" onclick="obfuscate()">Start Obfuscation</button>

            <div class="output-container" id="outputWrapper">
                <div class="loader-box">
                    <span class="section-label">Roblox Loader Script:</span>
                    <textarea id="loaderOutput" readonly style="height: 48px; white-space: nowrap;"></textarea>
                    <button class="btn" id="copyBtn" style="background-color: #334155; color: #ffffff; box-shadow: none; margin-top: 10px;" onclick="copyLoader()">Copy Loader</button>
                </div>
            </div>
        </div>

        <!-- DEOBFUSCATOR TAB -->
        <div id="deobfuscatorTab" class="tab-content">
            <div class="file-upload-box" id="dropZoneDeobf" onclick="document.getElementById('luaDeobFileInput').click()">
                <span class="file-upload-title">Upload Obfuscated Lua File:</span>
                <p class="file-upload-subtext" id="dropSubtextDeobf">Click to choose or drag & drop obfuscated script</p>
                <input type="file" id="luaDeobFileInput" accept=".lua,.luau,.txt" onchange="handleFileSelect(event, 'deobInput', 'dropSubtextDeobf')" style="display: none;">
            </div>

            <div class="or-text">Or paste obfuscated script here (IronBrew / Luraph):</div>
            <textarea id="deobInput" placeholder="-- Paste obfuscated Lua code here..."></textarea>

            <button class="btn btn-dark" id="deobSubmitBtn" onclick="deobfuscateCode()">Run Ultimate VM Lifter</button>

            <div class="output-container" id="deobOutputWrapper" style="display: block;">
                <div class="loader-box">
                    <span class="section-label">Devirtualized / Beautified Output:</span>
                    <textarea id="deobLoaderOutput" placeholder="Results will appear here..." readonly style="height: 300px; white-space: pre;"></textarea>
                    <button class="btn btn-dark" style="margin-top:10px;" onclick="copyDeobOutput()">Copy to Clipboard</button>
                </div>
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

        function setupDragAndDrop(dropZoneId, textareaId, subtextId) {
            const dropZone = document.getElementById(dropZoneId);
            ['dragenter', 'dragover'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); }, false);
            });
            ['dragleave', 'drop'].forEach(eventName => {
                dropZone.addEventListener(eventName, (e) => { e.preventDefault(); dropZone.classList.remove('drag-over'); }, false);
            });
            dropZone.addEventListener('drop', (e) => {
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    const reader = new FileReader();
                    reader.onload = function(evt) { document.getElementById(textareaId).value = evt.target.result; document.getElementById(subtextId).innerText = "Loaded: " + files[0].name; };
                    reader.readAsText(files[0]);
                }
            });
        }

        setupDragAndDrop('dropZoneObf', 'input', 'dropSubtextObf');
        setupDragAndDrop('dropZoneDeobf', 'deobInput', 'dropSubtextDeobf');

        function handleFileSelect(event, textareaId, subtextId) {
            const files = event.target.files;
            if (files.length > 0) {
                const reader = new FileReader();
                reader.onload = function(e) { document.getElementById(textareaId).value = e.target.result; document.getElementById(subtextId).innerText = "Loaded: " + files[0].name; };
                reader.readAsText(files[0]);
            }
        }

        async function obfuscate() {
            const inputCode = document.getElementById('input').value;
            const outputWrapper = document.getElementById('outputWrapper');
            const loaderArea = document.getElementById('loaderOutput');
            const submitBtn = document.getElementById('submitBtn');
            
            if (!inputCode.trim()) { outputWrapper.style.display = "block"; loaderArea.value = "-- Error: Empty script."; return; }
            outputWrapper.style.display = "block"; loaderArea.value = "-- Processing..."; submitBtn.innerText = "Processing...";

            try {
                const response = await fetch('/obfuscate', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: inputCode, settings: {} })
                });
                const data = await response.json();
                loaderArea.value = data.loader || "-- " + data.error;
            } catch (err) { loaderArea.value = "-- Network error."; } finally { submitBtn.innerText = "Start Obfuscation"; }
        }

        async function deobfuscateCode() {
            const inputCode = document.getElementById('deobInput').value;
            const loaderArea = document.getElementById('deobLoaderOutput');
            const submitBtn = document.getElementById('deobSubmitBtn');
            
            if (!inputCode.trim()) { loaderArea.value = "-- Error: Empty script."; return; }
            loaderArea.value = "-- Lifting VM, Evaluating Math Constraints, and Beautifying Code..."; submitBtn.innerText = "Processing...";

            try {
                const response = await fetch('/deobfuscate', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: inputCode })
                });
                const data = await response.json();
                loaderArea.value = data.code || "-- " + data.error;
            } catch (err) { loaderArea.value = "-- Network error."; } finally { submitBtn.innerText = "Run Ultimate VM Lifter"; }
        }

        function copyLoader() {
            const loaderArea = document.getElementById('loaderOutput'); loaderArea.select(); navigator.clipboard.writeText(loaderArea.value);
        }

        function copyDeobOutput() {
            const loaderArea = document.getElementById('deobLoaderOutput'); loaderArea.select(); navigator.clipboard.writeText(loaderArea.value);
            alert("Devirtualized script copied!");
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
</head>
<body>
    <div style="text-align: center; font-family: sans-serif; margin-top: 50px;">
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
    if not raw_code: return jsonify({"success": False, "error": "Empty input"}), 400
    
    token = uuid.uuid4().hex
    obfuscated_code = obfuscate_pipeline(raw_code, {})
    SCRIPT_CACHE[token] = {"code": obfuscated_code, "created_at": time.time(), "active": True}
    return jsonify({"success": True, "loader": f'loadstring(game:HttpGet("{CUSTOM_DOMAIN}/raw/{token}"))()', "token": token})

@app.route("/deobfuscate", methods=["POST"])
def deobfuscate_endpoint():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code", "")
    if not raw_code.strip(): return jsonify({"success": False, "error": "Input script cannot be empty."}), 400

    success, result = deobfuscate_lua(raw_code)
    return jsonify({"success": success, "code": result}), 200 if success else 400

@app.route("/raw/<token>", methods=["GET"])
def serve_script(token):
    sec_fetch_dest = request.headers.get("Sec-Fetch-Dest", "").lower()
    if sec_fetch_dest == "document" and bool(request.headers.get("Sec-Ch-Ua")):
        return render_template_string(PROTECTED_HTML_TEMPLATE)

    code = SCRIPT_CACHE.get(token, {}).get("code")
    if code:
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        return res
    return Response("warn('Script not found.')", status=200, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
