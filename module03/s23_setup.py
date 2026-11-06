"""Session 23 - one command to get your server ready. Run it from the COURSE repo folder:

    uv run python module03/s23_setup.py

It reads WORK_REPO from your .env, copies module03/s23_simple.py into YOUR work repo as s23/app.py, and prints the
exact commands for the rest of the lab (with your real paths filled in). Safe to run again: it never overwrites an
s23/app.py you already have, unless you add --fresh.
"""
import os
import shutil
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "module03" / "s23_simple.py"


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True), override=True)
    work = os.getenv("WORK_REPO", "").strip().strip('"')
    if not work:
        sys.exit("WORK_REPO is not set. Add this line to the .env in the course repo folder, then run again:\n"
                 "    WORK_REPO=C:\\path\\to\\your\\genai-course-work")
    repo = Path(work).expanduser()
    if not repo.is_dir():
        sys.exit(f"WORK_REPO points to {repo}, but that folder doesn't exist. Fix the WORK_REPO line in .env.")
    if repo.resolve() == ROOT:
        sys.exit("WORK_REPO points at the COURSE repo. It must be your own genai-course-work folder.")

    dst = repo / "s23" / "app.py"
    dst.parent.mkdir(exist_ok=True)
    if dst.exists() and "--fresh" not in sys.argv:
        print(f"Kept your existing {dst}  (add --fresh to start again from the original)")
    else:
        shutil.copy2(SRC, dst)
        print(f"Copied the server to {dst}")

    win = os.name == "nt"
    print("\nNext (stay in this course repo folder):")
    print(f"  Terminal 1, start the server:   uv run python \"{dst}\"")
    print("  Browser:                        http://127.0.0.1:8000/docs")
    print("  Terminal 2, the client:         uv run python module03" + ("\\" if win else "/") + "s23_client.py")
    print(f"  Edit in VS Code:                {dst}")
    print("  Checkpoint:                     uv run pytest tests/test_s23.py -rs")
    print(f"  Commit:                         cd \"{repo}\"  then  git add s23" + ("\\" if win else "/") + "app.py")


if __name__ == "__main__":
    main()
