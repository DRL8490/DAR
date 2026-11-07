import subprocess

def run(cmd):
    print(f"-> {' '.join(cmd)}")
    res = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
    if res.stdout.strip():
        print(res.stdout.strip())
    if res.stderr.strip():
        print(res.stderr.strip())
    return res

# 1. Ensure GitHub privacy-safe author is set
run(["git", "config", "user.name", "DRL8490"])
run(["git", "config", "user.email", "DRL8490@users.noreply.github.com"])

# 2.Create a permanent 1-command sync.py script for switching laptops effortlessly
sync_script = '''"""
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
'''

with open("sync.py", "w", encoding="utf-8") as f:
    f.write(sync_script)
print("1. Created permanent sync.py helper.")

# 3. Stage everything, pull remote commits from the other laptop with rebase, and push
run(["git", "add", "-A"])
run([
    "git", "commit",
    "--author=DRL8490 <DRL8490@users.noreply.github.com>",
    "-m", "chore: add sync.py and portable repo config"
])

print("\n2. Integrating commits from your other laptop (origin/main)...")
pull_res = run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"])
if pull_res.returncode != 0:
    run(["git", "rebase", "--abort"])
    run(["git", "pull", "--no-rebase", "--no-edit", "-X", "ours", "origin", "main"])

print("\n3. Pushing combined commits to GitHub...")
push_res = run(["git", "push", "origin", "main"])
if push_res.returncode == 0:
    print("\nSUCCESS! Both laptops and GitHub are now 100% in sync.")
