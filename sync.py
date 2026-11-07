"""
1-Command Multi-Laptop Git Sync Tool (sync.py)
Usage in VS Code Terminal:
    py sync.py
    py sync.py "optional custom commit message"
"""
import os
import sys
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOREPLY_AUTHOR = "DRL8490 <DRL8490@users.noreply.github.com>"

def run(cmd):
    print(f"-> {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=BASE_DIR, text=True, capture_output=True, encoding="utf-8")
    if res.stdout.strip():
        print(res.stdout.strip())
    if res.stderr.strip():
        print(res.stderr.strip())
    return res

def main():
    print("=== [1/4] Locking GitHub Privacy-Safe Author (GH007 Protection) ===")
    run(["git", "config", "user.name", "DRL8490"])
    run(["git", "config", "user.email", "DRL8490@users.noreply.github.com"])

    print("\n=== [2/4] Staging & Committing Local Laptop Changes ===")
    run(["git", "add", "-A"])
    status = subprocess.run(["git", "status", "--porcelain"], cwd=BASE_DIR, text=True, capture_output=True)
    if status.stdout.strip():
        custom_msg = " ".join(sys.argv[1:]).strip()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = custom_msg if custom_msg else f"sync: workspace update ({ts})"
        run(["git", "commit", f"--author={NOREPLY_AUTHOR}", "-m", commit_msg])
    else:
        print("No new local file edits to commit.")

    print("\n=== [3/4] Pulling & Integrating Updates from Other Laptop (origin/main) ===")
    run(["git", "fetch", "origin", "main"])
    pull_res = run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"])
    if pull_res.returncode != 0:
        print("Rebase conflict detected - falling back to automatic merge...")
        run(["git", "rebase", "--abort"])
        run(["git", "pull", "--no-rebase", "--no-edit", "-X", "ours", "origin", "main"])

    print("\n=== [4/4] Pushing Unified History to GitHub & Render ===")
    push_res = run(["git", "push", "origin", "main"])
    if push_res.returncode == 0:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, text=True, capture_output=True)
        print(f"\nSUCCESS! Commit {rev.stdout.strip()} is synced to GitHub and deploying to Render.")
    else:
        print("\nWARNING: Push encountered an issue. Check the git output above.")

if __name__ == "__main__":
    main()
