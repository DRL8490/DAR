"""
1-Command Multi-Laptop Git Sync Tool (sync.py)
Run `py sync.py` anytime you start or finish work on either laptop!
"""
import subprocess
from datetime import datetime

def run(cmd):
    print(f"-> {' '.join(cmd)}")
    return subprocess.run(cmd)

def main():
    run(["git", "config", "user.name", "DRL8490"])
    run(["git", "config", "user.email", "DRL8490@users.noreply.github.com"])

    # Stage and commit any local changes first
    run(["git", "add", "-A"])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    run([
        "git", "commit",
        "--author=DRL8490 <DRL8490@users.noreply.github.com>",
        "-m", f"sync: laptop workspace update ({ts})"
    ])

    # Pull and rebase on top of any commits pushed from the other laptop
    res = subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"])
    if res.returncode != 0:
        subprocess.run(["git", "rebase", "--abort"])
        run(["git", "pull", "--no-rebase", "--no-edit", "-X", "ours", "origin", "main"])

    # Push merged history to GitHub & Render
    run(["git", "push", "origin", "main"])

if __name__ == "__main__":
    main()
