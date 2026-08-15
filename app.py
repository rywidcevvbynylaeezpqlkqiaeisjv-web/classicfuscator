import math
import os
import random
import re
import sqlite3
import string
import time
import uuid
import ast
import operator
from flask import Flask, jsonify, render_template_string, request, Response
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

CUSTOM_DOMAIN = "https://classicfuscator.onrender.com"
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
# 1. ADVANCED DEOBFUSCATOR ENGINE (CFG DE-FLATTENER + MATH + HOOKS)
# ==============================================================================

class AdvancedLuaDeobfuscator:
    def __init__(self, code):
        self.code = code

    def strip_garbage(self):
        """Removes watermarks, junk comments, and dead spaces."""
        self.code = re.sub(r"--\[\[.*?\]\]--", "", self.code, flags=re.DOTALL)
        self.code = re.sub(r"--\[\[.*?\]\]", "", self.code, flags=re.DOTALL)
        self.code = re.sub(r"--[^\n]*", "", self.code)
        
    def fold_constants(self):
        """Recursively evaluates obfuscated math and boolean logic."""
        # Replace Lua 'a ^ b' with Python 'a ** b' for evaluation, handle math.floor
        def safe_eval(expr):
            expr = expr.replace('^', '**').replace('math.floor', 'math.floor')
            try:
                res = eval(expr, {"math": math})
                if isinstance(res, float) and res.is_integer():
                    return str(int(res))
                return str(res)
            except Exception:
                return None

        # Fold innermost parentheses first (recursive)
        pattern = re.compile(r'\(([\d\s\+\-\*/\.\^]+)\)')
        old_code = ""
        while old_code != self.code:
            old_code = self.code
            def replacer(match):
                res = safe_eval(match.group(1))
                return res if res is not None else match.group(0)
            self.code = pattern.sub(replacer, self.code)

        # Fold Boolean traps
        def bool_eval(match):
            try:
                left, right = float(match.group(1)), float(match.group(2))
                return "true" if left == right else "false"
            except:
                return match.group(0)
        self.code = re.sub(r'\(\s*(\d+(?:\.\d+)?)\s*==\s*(\d+(?:\.\d+)?)\s*\)', bool_eval, self.code)
        self.code = re.sub(r'\(\s*\{\s*\[0\]\s*=\s*nil\s*\}\s*\[1\]\s*\)', "nil", self.code)
        self.code = re.sub(r'not\s*\(not\s*true\)', 'true', self.code)
        self.code = re.sub(r'not\s*\(not\s*false\)', 'false', self.code)

    def deflatten_control_flow(self):
        """
        Attempts to defeat Control Flow Flattening (IronBrew/Luraph style).
        Looks for: local state = X; while true do if state == X then ... state = Y ...
        """
        # 1. Find state variable initialization
        state_match = re.search(r'local\s+([a-zA-Z_]\w*)\s*=\s*(\d+|0x[0-9a-fA-F]+)\s*;?\s*while\s+true\s+do', self.code)
        if not state_match:
            # Try alternate pattern (Ironbrew specific: repeat ... until state == X)
            state_match = re.search(r'local\s+([a-zA-Z_]\w*)\s*=\s*(-?\d+|-?0x[0-9a-fA-F]+)\s*repeat', self.code)
            
        if not state_match:
            return # Cannot find flattening state variable

        state_var = state_match.group(1)
        try:
            current_state = int(state_match.group(2), 0)
        except:
            return

        # 2. Extract blocks mapped to their state requirement
        # Pattern: if state == 123 then [CODE] state = 456 end
        block_pattern = re.compile(r'if\s*(?:not\s*\(\s*)?' + state_var + r'\s*(?:~=|<|>|<=|>=|==)\s*(-?\d+|-?0x[0-9a-fA-F]+)\s*\)?\s*then\s*(.*?)(?:elseif|else|end)', re.DOTALL)
        
        blocks = {}
        for match in block_pattern.finditer(self.code):
            val = int(match.group(1), 0)
            code_block = match.group(2).strip()
            
            # Find next state assignment in this block
            next_state_match = re.search(r'' + state_var + r'\s*=\s*(-?\d+|-?0x[0-9a-fA-F]+)', code_block)
            next_state = int(next_state_match.group(1), 0) if next_state_match else None
            
            blocks[val] = {"code": code_block, "next": next_state}

        if not blocks:
            return

        # 3. Simulate execution to unroll the blocks
        unrolled = []
        visited = set()
        
        while current_state in blocks and current_state not in visited:
            visited.add(current_state)
            block = blocks[current_state]
            
            # Clean the state assignment out of the code
            clean_code = re.sub(r'' + state_var + r'\s*=\s*(-?\d+|-?0x[0-9a-fA-F]+)\s*;?', '', block["code"]).strip()
            if clean_code:
                unrolled.append(clean_code)
                
            current_state = block["next"]

        if unrolled:
            unrolled_code = "\n".join(unrolled)
            # Replace the entire while/repeat loop with the unrolled code
            # (This is a destructive heuristic, we prepend it as a recovered block)
            self.code = "-- [DE-FLATTENED CONTROL FLOW RECOVERED] --\n" + unrolled_code + "\n\n-- [ORIGINAL OBFUSCATED VM BELOW] --\n" + self.code

    def inject_dynamic_interceptor(self):
        """
        Injects a payload at the top of the script that hooks `loadstring`, `setfenv`, 
        and `pcall` to catch the VM attempting to execute the decrypted original script.
        """
        interceptor = """
-- [DYNAMIC INTERCEPTOR INJECTED BY CLASSICFUSCATOR] --
-- Execute this script in Roblox Studio to dump the decrypted source.
local _REAL_LOADSTRING = loadstring or load
if _REAL_LOADSTRING then
    getfenv().loadstring = function(str, chunkname)
        print("\\n\\n--- [DECRYPTED PAYLOAD INTERCEPTED] ---")
        print(str)
        print("---------------------------------------\\n\\n")
        return _REAL_LOADSTRING(str, chunkname)
    end
end

local _REAL_SETFENV = setfenv
if _REAL_SETFENV then
    getfenv().setfenv = function(f, env)
        if type(f) == "function" then
            local info = debug.getinfo(f)
            print("[VM Environment Hook Detected]")
        end
        return _REAL_SETFENV(f, env)
    end
end
-- [END INTERCEPTOR] --

"""
        self.code = interceptor + self.code

    def beautify(self):
        """Advanced Lexical Formatter to make VM structures readable."""
        # Add spaces around symbols
        self.code = re.sub(r'([=+\-*/%^<>~]=?)', r' \1 ', self.code)
        self.code = re.sub(r',', r', ', self.code)
        self.code = re.sub(r';', r';\n', self.code)
        self.code = re.sub(r'\b(then|do|repeat)\b', r'\1\n', self.code)
        self.code = re.sub(r'\b(end|until|elseif|else)\b', r'\n\1\n', self.code)
        
        lines = [l.strip() for l in self.code.split('\n') if l.strip()]
        out = []
        indent = 0
        
        indent_inc = ['do', 'then', 'repeat', 'function']
        indent_dec = ['end', 'until', 'elseif', 'else']

        for line in lines:
            # Dedent before adding line
            if any(line.startswith(word) for word in indent_dec):
                indent = max(0, indent - 1)
                
            out.append(("    " * indent) + line)
            
            # Calculate next indentation
            words = re.findall(r'\b[a-zA-Z_]+\b', line)
            for word in words:
                if word in indent_inc:
                    indent += 1
                elif word in indent_dec and word not in ['elseif', 'else']: # already handled
                    indent = max(0, indent - 1)

        self.code = "\n".join(out)

    def process(self):
        self.strip_garbage()
        self.fold_constants()
        self.deflatten_control_flow()
        self.beautify()
        self.inject_dynamic_interceptor()
        return True, self.code

def deobfuscate_lua(lua_code: str) -> tuple[bool, str]:
    deobfuscator = AdvancedLuaDeobfuscator(lua_code)
    return deobfuscator.process()


# ==============================================================================
# 2. OBFUSCATOR ENGINE (No changes needed here from previous update)
# ==============================================================================
# ... [KEEP YOUR EXISTING OBFUSCATOR FUNCTIONS HERE] ...
# (random_id, ror, TOKEN_REGEX, decode_lua_string_bytes, transform_number, transform_string, ast_obfuscate, build_vm_layer, obfuscate_pipeline, validate_lua_syntax)

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

def validate_lua_syntax(lua_code: str) -> tuple[bool, str]: return True, "" # Simplified for brevity, keep your original

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
# 5. LIGHT THEME CATEGORY DASHBOARD & API
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
        .card { background: #ffffff; border-radius: 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03); width: 100%; max-width: 680px; padding: 36px 32px; border: 1px solid #eef0f4; }
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
        .setting-group { margin-bottom: 18px; background: #f8fafc; padding: 14px 16px; border-radius: 12px; border: 1px solid #eef2f6; }
        .setting-header { display: flex; justify-content: space-between; align-items: center; }
        .setting-title { font-size: 14px; font-weight: 600; color: #1e293b; }
        .setting-desc { font-size: 12px; color: #64748b; margin-top: 4px; }
        .setting-select, .setting-input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; outline: none; background: #ffffff; color: #1e293b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Classicfuscator & High-Tier Deobfuscator</h1>

        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('obfuscatorTab', this)">1. Obfuscator</button>
            <button class="tab-btn" onclick="switchTab('deobfuscatorTab', this)">2. Advanced Deobfuscator</button>
            <button class="tab-btn" onclick="switchTab('settingsTab', this)">3. Settings</button>
        </div>

        <!-- OBFUSCATOR TAB -->
        <div id="obfuscatorTab" class="tab-content active">
            <textarea id="input" placeholder="print('Testing Classicfuscator Enterprise!')"></textarea>
            <button class="btn" id="submitBtn" onclick="obfuscate()">Start Obfuscation</button>
            <div class="output-container" id="outputWrapper">
                <div class="loader-box">
                    <span class="section-label">Roblox Loader Script:</span>
                    <textarea id="loaderOutput" readonly style="height: 48px; white-space: nowrap;"></textarea>
                </div>
            </div>
        </div>

        <!-- DEOBFUSCATOR TAB -->
        <div id="deobfuscatorTab" class="tab-content">
            <textarea id="deobInput" placeholder="-- Paste IronBrew, Luraph, MoonSec, or PSU code here..."></textarea>
            <button class="btn btn-dark" id="deobSubmitBtn" onclick="deobfuscateCode()">Analyze & Deobfuscate</button>
            <div class="output-container" id="deobOutputWrapper" style="display: block;">
                <div class="loader-box">
                    <span class="section-label">Deobfuscated / Beautified / Hooked Output:</span>
                    <textarea id="deobLoaderOutput" placeholder="Results will appear here..." readonly style="height: 250px;"></textarea>
                    <button class="btn btn-dark" style="margin-top:10px;" onclick="copyDeobOutput()">Copy to Clipboard</button>
                </div>
            </div>
        </div>

        <!-- SETTINGS TAB -->
        <div id="settingsTab" class="tab-content">
            <div class="setting-group"><div class="setting-header"><div><div class="setting-title">VM Virtualization Layers</div></div><select id="cfgLayers" class="setting-select"><option value="1">1 Layer</option></select></div></div>
        </div>
    </div>

    <script>
        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
        }

        async function obfuscate() {
            // Your obfuscate logic here
        }

        async function deobfuscateCode() {
            const inputCode = document.getElementById('deobInput').value;
            const loaderArea = document.getElementById('deobLoaderOutput');
            const submitBtn = document.getElementById('deobSubmitBtn');
            
            if (!inputCode.trim()) {
                loaderArea.value = "-- Error: Input script is empty."; return;
            }

            loaderArea.value = "-- Unrolling CFG, folding constants, and formatting...";
            submitBtn.innerText = "Processing...";

            try {
                const response = await fetch('/deobfuscate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: inputCode })
                });

                const data = await response.json();
                loaderArea.value = data.code || "-- " + data.error;
            } catch (err) {
                loaderArea.value = "-- Network error: Could not connect to server.";
            } finally {
                submitBtn.innerText = "Analyze & Deobfuscate";
            }
        }

        function copyDeobOutput() {
            const loaderArea = document.getElementById('deobLoaderOutput');
            loaderArea.select();
            navigator.clipboard.writeText(loaderArea.value);
            alert("Copied!");
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
    settings = data.get("settings", {})
    if not raw_code: return jsonify({"success": False, "error": "Empty input"}), 400
    
    token = uuid.uuid4().hex
    obfuscated_code = obfuscate_pipeline(raw_code, settings)
    SCRIPT_CACHE[token] = {"code": obfuscated_code, "created_at": time.time(), "active": True}
    
    return jsonify({"success": True, "loader": f'loadstring(game:HttpGet("{CUSTOM_DOMAIN}/raw/{token}"))()', "token": token})

@app.route("/deobfuscate", methods=["POST"])
def deobfuscate_endpoint():
    data = request.get_json(silent=True) or {}
    raw_code = data.get("code", "")
    
    if not raw_code.strip():
        return jsonify({"success": False, "error": "Input script cannot be empty."}), 400

    success, result = deobfuscate_lua(raw_code)
    return jsonify({"success": success, "code": result}), 200 if success else 400

@app.route("/raw/<token>", methods=["GET"])
def serve_script(token):
    code = SCRIPT_CACHE.get(token, {}).get("code")
    if code:
        res = Response(code, mimetype="text/plain")
        res.headers["Access-Control-Allow-Origin"] = "*"
        return res
    return Response("warn('Script not found.')", status=200, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
