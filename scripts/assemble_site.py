"""Copy the built site into _site for publishing, leaving out code, tests and private status files."""
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
SKIP = {".git", ".github", "scripts", "tests", "_site", "README.md", ".gitignore",
        "mailerlite-status.json", "weekly-email-status.json", "__pycache__", ".pytest_cache"}

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
for item in ROOT.iterdir():
    if item.name in SKIP:
        continue
    if item.is_dir():
        shutil.copytree(item, OUT / item.name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(item, OUT / item.name)
print("Site ready:", ", ".join(sorted(p.name for p in OUT.iterdir())))
