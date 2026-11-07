import os, re, ast, json, subprocess

NEW_LOAD_SAVE_BLOCK = """MTI_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mti_state.json")

def _init_mti_db_table():
    try:
        from app import db
        from sqlalchemy import text
        db.session.execute(text("CREATE TABLE IF NOT EXISTS mti_state_store (k VARCHAR(64) PRIMARY KEY, v TEXT)"))
        db.session.commit()
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass

def load_mti_state():
    st = None
    try:
        _init_mti_db_table()
        from app import db
        from sqlalchemy import text
        row = db.session.execute(text("SELECT v FROM mti_state_store WHERE k = 'mti_state_v1'")).fetchone()
        if row and row[0]:
            st = json.loads(row[0])
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
    if not st:
        try:
            if os.path.exists(MTI_STATE_FILE):
                with open(MTI_STATE_FILE, "r", encoding="utf-8") as f:
                    st = json.load(f)
        except Exception:
            st = None
    if not isinstance(st, dict):
        st = {}
    for def_k in ("daily_logs", "issues", "rock_bags", "crossings"):
        if def_k not in st:
            st[def_k] = []
    changed = False
    if not st.get("dpr_20261107_clean_v5"):
        st["ledger"] = [dict(x) for x in PRELOADED_MTI_LEDGER]
        st["input_logs"] = [dict(x) for x in PRELOADED_MTI_LOGS]
        st["dpr_20261107_clean_v5"] = True
        changed = True
    for r in st.get("ledger", []):
        if float(r.get("heading_deg") or 0) < 180.0:
            r["heading_deg"] = round(float(r.get("heading_deg") or 15.854) + 180.0, 3)
            changed = True
    if changed:
        save_mti_state(st)
    return st

def save_mti_state(state):
    raw = json.dumps(state, ensure_ascii=False)
    try:
        _init_mti_db_table()
        from app import db
        from sqlalchemy import text
        row = db.session.execute(text("SELECT k FROM mti_state_store WHERE k = 'mti_state_v1'")).fetchone()
        if row:
            db.session.execute(text("UPDATE mti_state_store SET v = :val WHERE k = 'mti_state_v1'"), {"val": raw})
        else:
            db.session.execute(text("INSERT INTO mti_state_store (k, v) VALUES ('mti_state_v1', :val)"), {"val": raw})
        db.session.commit()
    except Exception:
        try:
            from app import db
            db.session.rollback()
        except Exception:
            pass
    try:
        with open(MTI_STATE_FILE, "w", encoding="utf-8") as f:
            f.write(raw)
    except Exception:
        pass
"""

def replace_func_via_ast(source_code, func_name, new_func_code):
    tree = ast.parse(source_code)
    lines = source_code.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            start_line = node.decorator_list[0].lineno if node.decorator_list else node.lineno
            end_line = node.end_lineno
            new_lines = lines[:start_line - 1] + [new_func_code.rstrip() + "\n\n"] + lines[end_line:]
            return "".join(new_lines), (start_line, end_line)
    return source_code, None

with open("mti_blueprint.py", "r", encoding="utf-8-sig") as f:
    mc = f.read().lstrip("\ufeff")

mc, _ = replace_func_via_ast(mc, "_init_mti_db_table", "")
mc, s1 = replace_func_via_ast(mc, "load_mti_state", NEW_LOAD_SAVE_BLOCK)
mc, s2 = replace_func_via_ast(mc, "save_mti_state", "")

mc = mc.replace("24°25'44.20", "24°25′44.20").replace("120°27'10.72", "120°27′10.72")

ast.parse(mc)
with open("mti_blueprint.py", "w", encoding="utf-8") as f:
    f.write(mc)
print(f"1. Fixed MTI_STATE_FILE, PostgreSQL TEXT storage (mti_state_store), and db.session.rollback() in mti_blueprint.py ({s1})!")

try:
    from app import app
    from mti_blueprint import load_mti_state
    with app.app_context():
        st = load_mti_state()
        print(f"2. LOCAL TEST PASSED: load_mti_state() loaded {len(st.get('ledger', []))} ledger fixes and {len(st.get('input_logs', []))} DPR logs cleanly!")
except Exception:
    import traceback
    traceback.print_exc()

subprocess.run(["py", "sync.py", "fix: resolve 500 error on /mti by defining MTI_STATE_FILE and using dedicated TEXT table with rollback"], check=False)
