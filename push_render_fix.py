import os
import json
import urllib.request
import subprocess

def run_cmd(cmd):
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
    if res.stdout.strip():
        print(res.stdout.strip())
    if res.stderr.strip():
        print(res.stderr.strip())
    return res

# 1. Fetch official GitHub numeric ID for DRL8490 to satisfy GH007 strict noreply format
noreply_email = "DRL8490@users.noreply.github.com"
try:
    req = urllib.request.Request(
        "https://api.github.com/users/DRL8490",
        headers={"User-Agent": "Python-Git-Fixer"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if "id" in data:
            noreply_email = f"{data['id']}+DRL8490@users.noreply.github.com"
except Exception as e:
    print(f"Note: Using fallback noreply ({e})")

print(f"\n[Step 1] Using GitHub privacy-safe email: {noreply_email}")
run_cmd(["git", "config", "--global", "user.name", "DRL8490"])
run_cmd(["git", "config", "--global", "user.email", noreply_email])
run_cmd(["git", "config", "user.name", "DRL8490"])
run_cmd(["git", "config", "user.email", noreply_email])

# 2. Write clean Python 3.11.8 compatible requirements.txt (no numpy==2.5.4!)
clean_requirements = """APScheduler==3.10.4
blinker>=1.7.0
click>=8.1.7,<8.5.0
docxtpl>=0.16.7
et_xmlfile>=1.1.0
Flask>=3.0.0
Flask-Login>=0.6.3
Flask-Mail>=0.9.1
Flask-SQLAlchemy>=3.1.1
gunicorn>=21.2.0
itsdangerous>=2.1.2
Jinja2>=3.1.2
lxml>=5.0.0,<6.0.0
MarkupSafe>=2.1.3
numpy>=1.26.4,<2.5.0
openpyxl>=3.1.2
pandas>=2.1.0,<3.0.0
psycopg2-binary>=2.9.9
python-docx>=1.1.0
pypdf>=4.0.0
SQLAlchemy>=2.0.0
Werkzeug>=3.0.0
"""

with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write(clean_requirements)

print("\n[Step 2] Wrote clean requirements.txt (numpy==2.5.4 removed).")

# 3. Collapse any unpushed commits that had your private email into one clean commit
print("\n[Step 3] Resetting unpushed commit metadata to remove private email...")
run_cmd(["git", "fetch", "origin", "main"])
run_cmd(["git", "reset", "--soft", "origin/main"])
run_cmd(["git", "add", "-A"])
run_cmd([
    "git", "commit",
    f"--author=DRL8490 <{noreply_email}>",
    "-m", "fix: make requirements.txt compatible with Render Python 3.11.8"
])

# 4. Print new local commit hash and push to GitHub
rev = run_cmd(["git", "rev-parse", "--short", "HEAD"])
print(f"\n[Step 4] Pushing new commit ({rev.stdout.strip()}) to GitHub...")
push_res = subprocess.run(["git", "push", "origin", "main"])

if push_res.returncode == 0:
    print(f"\nSUCCESS! New commit {rev.stdout.strip()} is now on GitHub (old commit d05e2db is replaced).")
else:
    print("\nWARNING: git push returned an error above. Please copy and paste the terminal output here.")
