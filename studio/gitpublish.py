"""Commit and push the public site. Never force-pushes."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

MAX_FILE_BYTES = 8_000_000
EXACT = {
    "data/site.json",
    "data/works.json",
    "sitemap.xml",
    "llms.txt",
    "MAINTAIN.md",
    ".gitignore",
    "og.jpg",
}
IMAGE_SUFFIXES = (".jpg", ".jpeg")
PLACE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class GitError(Exception):
    def __init__(self, message: str, output: str = ""):
        super().__init__(message)
        self.output = output


def parse_porcelain(text: str) -> list[str]:
    paths = []
    for line in text.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        rest = line[3:]
        if rest.startswith('"') and rest.endswith('"'):
            rest = rest[1:-1]
        rename = "R" in status or "C" in status
        if rename and " -> " in rest:
            old, new = rest.split(" -> ", 1)
            paths.extend([new.strip(), old.strip()])
            continue
        paths.append(rest.strip())
    return paths


def is_allowed(path: str) -> bool:
    path = path.replace("\\", "/").strip()
    if path.endswith("/"):
        path = path[:-1]
    if not path or path.startswith("/") or path.startswith("~"):
        return False
    parts = Path(path).parts
    if ".." in parts:
        return False
    if path in EXACT:
        return True
    if parts[0] == "works":
        if len(parts) == 1:
            return True
        name = parts[-1]
        return name == "index.html" or name.lower().endswith(IMAGE_SUFFIXES)
    if parts[0] == "images" and len(parts) == 2:
        return parts[-1].lower().endswith(IMAGE_SUFFIXES)
    if parts[0] == "images" and len(parts) == 3 and PLACE_ID.fullmatch(parts[1]):
        name = parts[-1]
        return name == "index.html" or name.lower().endswith(IMAGE_SUFFIXES)
    return False


def files_to_commit(root: Path, porcelain: str) -> tuple[list[str], list[str]]:
    allowed: list[str] = []
    blocked: list[str] = []
    for raw in parse_porcelain(porcelain):
        path = raw[:-1] if raw.endswith("/") else raw
        if not is_allowed(path) and not (root / path).is_dir():
            blocked.append(path)
            continue
        full = root / path
        if full.is_dir():
            for child in sorted(full.rglob("*")):
                if not child.is_file():
                    continue
                rel = child.relative_to(root).as_posix()
                (allowed if is_allowed(rel) else blocked).append(rel)
            continue
        if is_allowed(path):
            allowed.append(path)
        else:
            blocked.append(path)
    return _unique(allowed), _unique(blocked)


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def assert_sizes(root: Path, paths: list[str]) -> None:
    for path in paths:
        full = root / path
        if full.is_file() and full.stat().st_size > MAX_FILE_BYTES:
            raise GitError(f"{path} ist größer als 8 MB und wird nicht veröffentlicht.")


def run_git(args: list[str], root: Path) -> str:
    proc = subprocess.run(args, cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise GitError(detail or "Git ist fehlgeschlagen.", detail)
    return proc.stdout


def ssh_result(agent_code: int, remote_text: str) -> tuple[bool, str]:
    if agent_code != 0:
        return False, "Kein Schlüssel im ssh-agent. Bitte ssh-add ausführen und die Seite neu laden."
    if "successfully authenticated" in remote_text.lower():
        return True, remote_text.strip()
    return False, remote_text.strip() or "GitHub hat den Schlüssel nicht angenommen."


def github_account(message: str) -> str:
    import re

    match = re.search(r"Hi ([^!]+)!", message)
    return match.group(1) if match else ""


def check_github_ssh() -> tuple[bool, str]:
    agent = subprocess.run(["ssh-add", "-l"], capture_output=True, text=True)
    remote = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-T", "git@github.com"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return ssh_result(agent.returncode, remote.stdout + remote.stderr)


def inspect_status(root: Path, runner=run_git) -> dict:
    try:
        text = runner(["git", "status", "--porcelain"], root)
    except GitError as exc:
        return {"allowed": [], "blocked": [], "error": str(exc)}
    allowed, blocked = files_to_commit(root, text)
    too_big = ""
    try:
        assert_sizes(root, allowed)
    except GitError as exc:
        too_big = str(exc)
    return {"allowed": allowed, "blocked": blocked, "error": None, "too_big": too_big}


def validate_message(message: str) -> str:
    message = (message or "").strip()
    if not message or "\n" in message or "\r" in message:
        raise GitError("Die Nachricht muss eine Zeile sein.")
    if len(message) > 200:
        raise GitError("Die Nachricht ist zu lang (höchstens 200 Zeichen).")
    return message


def publish(root: Path, message: str, runner=run_git, ssh_ok: bool = True) -> dict:
    if not ssh_ok:
        raise GitError("Kein GitHub-Schlüssel im ssh-agent.")
    message = validate_message(message)

    def collect():
        return files_to_commit(root, runner(["git", "status", "--porcelain"], root))

    allowed, blocked = collect()
    if not allowed:
        raise GitError("Nichts zu veröffentlichen.")
    assert_sizes(root, allowed)
    runner(["git", "pull", "--ff-only", "origin", "main"], root)
    allowed, blocked = collect()
    if not allowed:
        raise GitError("Nichts zu veröffentlichen.")
    assert_sizes(root, allowed)
    runner(["git", "add", "--", *allowed], root)
    staged = _staged(runner, root)
    extra = [path for path in staged if not is_allowed(path)]
    if extra:
        runner(["git", "reset", "-q", "HEAD", "--", *extra], root)
        staged = _staged(runner, root)
        extra = [path for path in staged if not is_allowed(path)]
        if extra:
            raise GitError("Veröffentlichen abgebrochen. Unerwartete Dateien: " + ", ".join(extra))
    if not staged:
        raise GitError("Nichts zu veröffentlichen.")
    runner(["git", "commit", "-m", message], root)
    runner(["git", "push", "origin", "main"], root)
    return {"committed": staged, "blocked": blocked}


def _staged(runner, root: Path) -> list[str]:
    text = runner(["git", "diff", "--cached", "--name-only"], root)
    return [line for line in text.splitlines() if line.strip()]


def ensure_identity(root: Path) -> None:
    run_git(["git", "config", "user.name", "Thorsten Weitz"], root)
    run_git(["git", "config", "user.email", "Wtho.Art@proton.me"], root)


def read_identity(root: Path) -> tuple[str, str]:
    name = run_git(["git", "config", "user.name"], root).strip()
    email = run_git(["git", "config", "user.email"], root).strip()
    return name, email
