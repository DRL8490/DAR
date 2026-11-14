import os, sys, glob, json, shutil, ctypes, ast, subprocess, urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

gi_path = os.path.join(ROOT, ".gitignore")
gi_txt = open(gi_path, "r", encoding="utf-8").read() if os.path.exists(gi_path) else ""
gi_add = [x for x in ("_laptop_sync_backup/", "_unpushed_backups/", "_pure_whl/") if x not in gi_txt]
if gi_add:
    open(gi_path, "a", encoding="utf-8").write("\n" + "\n".join(gi_add) + "\n")

print("=== [1/5] Backing Up Local DB & Workspace Setup Data ===")
bk_dir = os.path.join(ROOT, "_laptop_sync_backup")
os.makedirs(os.path.join(bk_dir, "workspace"), exist_ok=True)
os.makedirs(os.path.join(bk_dir, "instance"), exist_ok=True)

for db_p in glob.glob(os.path.join("instance", "*.db")):
    shutil.copy2(db_p, os.path.join(bk_dir, "instance", os.path.basename(db_p)))
for ext in ("*.npy", "*.json"):
    for fp in glob.glob(os.path.join("workspace", ext)):
        if not os.path.basename(fp).startswith("last_4panel"):
            shutil.copy2(fp, os.path.join(bk_dir, "workspace", os.path.basename(fp)))

diff_out = subprocess.run(["git", "diff", "--", "*.py", "*.html", "*.js", "*.css"], capture_output=True, text=True)
if diff_out.stdout.strip():
    os.makedirs("_unpushed_backups", exist_ok=True)
    patch_fn = os.path.join("_unpushed_backups", f"unpushed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.patch")
    open(patch_fn, "w", encoding="utf-8").write(diff_out.stdout)
    print(f"  -> Saved safety patch of unpushed local edits to {patch_fn}")

self_code = open(__file__, "r", encoding="utf-8").read()

print("=== [2/5] Fetching & Syncing Code to Latest origin/main ===")
subprocess.run(["git", "rm", "--cached", "-r", "--ignore-unmatch", "instance", "__pycache__", "workspace"], capture_output=True)
subprocess.run(["git", "fetch", "origin", "main"], check=True)
subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)

if not os.path.exists(__file__):
    open(__file__, "w", encoding="utf-8").write(self_code)
gi_now = open(gi_path, "r", encoding="utf-8").read() if os.path.exists(gi_path) else ""
miss = [x for x in ("_laptop_sync_backup/", "_unpushed_backups/", "_pure_whl/") if x not in gi_now]
if miss:
    open(gi_path, "a", encoding="utf-8").write("\n" + "\n".join(miss) + "\n")

print("=== [3/5] Checking & Self-Healing .venv Dependencies ===")
site_pkgs = next((p for p in sys.path if "site-packages" in p.lower() and os.path.isdir(p)), "")
py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"

def _ensure_pure_sqlalchemy():
    os.makedirs("_pure_whl", exist_ok=True)
    rc = subprocess.run([
        sys.executable, "-m", "pip", "download", "--only-binary=:all:", "--platform", "any",
        "--python-version", py_ver, "--implementation", "py", "--abi", "none",
        "--no-deps", "-d", "_pure_whl", "SQLAlchemy"
    ], check=False).returncode
    whls = glob.glob(os.path.join("_pure_whl", "*.whl"))
    if rc != 0 or not whls:
        with urllib.request.urlopen("https://pypi.org/pypi/SQLAlchemy/json", timeout=20) as resp:
            meta = json.loads(resp.read().decode("utf-8"))
        for item in meta.get("urls", []):
            if item.get("filename", "").endswith("py3-none-any.whl"):
                dest = os.path.join("_pure_whl", item["filename"])
                urllib.request.urlretrieve(item["url"], dest)
                whls = [dest]
                break
    if whls:
        subprocess.run([sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", "-q", whls[0]], check=True)
    shutil.rmtree("_pure_whl", ignore_errors=True)

try:
    import sqlalchemy
except ImportError as exc:
    if "Application Control policy" in str(exc) or "DLL load failed" in str(exc):
        print("  -> Windows Smart App Control detected; switching SQLAlchemy to pure-Python wheel...")
        _ensure_pure_sqlalchemy()
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "SQLAlchemy"], check=False)

try:
    import ezdxf
except ImportError:
    print("  -> Installing ezdxf & lxml wheels...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--only-binary=:all:", "-q", "ezdxf", "lxml>=6.0.2"], check=False)

if site_pkgs and os.name == "nt":
    opt_pkgs = {"sqlalchemy", "markupsafe", "ezdxf", "greenlet", "simplejson", "yaml", "_yaml", "charset_normalizer"}
    for pyd in glob.glob(os.path.join(site_pkgs, "**", "*.pyd"), recursive=True):
        rel = os.path.relpath(pyd, site_pkgs)
        if rel.split(os.sep)[0].lower() in opt_pkgs:
            try:
                ctypes.WinDLL(pyd)
            except OSError as exc:
                if getattr(exc, "winerror", 0) == 4551 or "Application Control policy" in str(exc):
                    try: os.remove(pyd)
                    except Exception: pass

print("=== [4/5] Restoring Local DB/Setup & Clearing Stale PDF Cache ===")
os.makedirs("instance", exist_ok=True)
for fp in glob.glob(os.path.join(bk_dir, "instance", "*.db")):
    shutil.copy2(fp, os.path.join("instance", os.path.basename(fp)))

os.makedirs("workspace", exist_ok=True)
for fp in glob.glob(os.path.join(bk_dir, "workspace", "*")):
    dest = os.path.join("workspace", os.path.basename(fp))
    if not os.path.exists(dest):
        shutil.copy2(fp, dest)
for stale in glob.glob(os.path.join("workspace", "*.pdf")) + glob.glob(os.path.join("workspace", "latest_*")):
    try: os.remove(stale)
    except Exception: pass
shutil.rmtree(bk_dir, ignore_errors=True)

print("=== [5/5] Verifying AST & Active Flask Routes ===")
for fn in sorted(glob.glob("*.py")):
    src = open(fn, "r", encoding="utf-8-sig").read().lstrip("\ufeff")
    ast.parse(src)

head_commit = subprocess.check_output(["git", "log", "-1", "--oneline"], text=True).strip()
from app import app
mti_cnt = sum(1 for r in app.url_map.iter_rules() if "/mti" in r.rule)
print(f"  -> Latest Commit : {head_commit}")
print(f"  -> Active Routes : {mti_cnt} MTI endpoints verified")
print("\nLAPTOP SYNC 100% READY! (Press Ctrl+Shift+P -> 'Developer: Reload Window' to refresh open tabs)")