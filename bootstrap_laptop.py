"""
1-Command Laptop Bootstrapper & Sync Tool for DAR / THPP Survey App.
Whenever you move to a different laptop, open terminal and run:
    py bootstrap_laptop.py
"""
import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, ".venv")
VENV_PY = os.path.join(VENV_DIR, "Scripts", "python.exe") if os.name == "nt" else os.path.join(VENV_DIR, "bin", "python")

def run(cmd):
    print(f"-> {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=BASE_DIR)

def main():
    print("=== [1/4] Configuring Git Author & Privacy-Safe Email (GH007 Safe) ===")
    run(["git", "config", "user.name", "DRL8490"])
    run(["git", "config", "user.email", "DRL8490@users.noreply.github.com"])

    print("\n=== [2/4] Pulling Latest Code from GitHub (origin/main) ===")
    run(["git", "pull", "origin", "main"])

    print("\n=== [3/4] Checking Local Virtual Environment (.venv) ===")
    need_rebuild = False
    if not os.path.exists(VENV_PY):
        need_rebuild = True
    else:
        chk = subprocess.run([VENV_PY, "-c", "import sys; print(sys.executable)"], capture_output=True, text=True)
        if chk.returncode != 0:
            need_rebuild = True

    if need_rebuild:
        print("Building fresh .venv for this laptop...")
        if os.path.exists(VENV_DIR):
            import shutil
            shutil.rmtree(VENV_DIR, ignore_errors=True)
        run([sys.executable, "-m", "venv", ".venv"])
    else:
        print(".venv is healthy on this laptop.")

    print("\n=== [4/4] Installing / Verifying Packages from requirements.txt ===")
    run([VENV_PY, "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    run([VENV_PY, "-m", "pip", "install", "-r", "requirements.txt"])

    print("\n==================================================================")
    print("LAPTOP READY! Activate your environment in PowerShell with:")
    print("    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force")
    print("    .\.venv\Scripts\Activate.ps1")
    print("    python app.py")
    print("==================================================================")

if __name__ == "__main__":
    main()
