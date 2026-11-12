"""Deterministic helpers for the project-setup skill.

    python workbench.py diagnose [ROOT] [--json]   read-only checks for one project
    python workbench.py install-codex [--force]    copy this plugin's skills to $CODEX_HOME/skills

Only the standard library is used. Personal settings are read from ~/.agent-workbench.toml
(see config.example.toml at the repository root); every setting is optional.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2]  # <plugin>/skills
CONFIG_PATH = Path.home() / ".agent-workbench.toml"
MT_SKILLS = ("mt-write", "mt-publish", "mt-master-module")
GRILL_SKILLS = ("grill-me", "grilling")
GOAL_LOOP_MARK = "<!-- goal-loop:begin"
SETUP_MARK = "<!-- project-setup:begin"


def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def run(args: list[str], cwd: Path) -> tuple[int, str]:
    try:
        done = subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    return done.returncode, done.stdout


def same_path(a: str | Path, b: str | Path) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def memory_base(root: Path) -> tuple[str, bool]:
    """The knowledge base folder name and whether a .memory-tool.yml pointer names it."""
    pointer = root / ".memory-tool.yml"
    if pointer.is_file():
        for line in pointer.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "base":
                return value.strip().strip("\"'") or ".memory", True
    return os.environ.get("MEMORY_TOOL_BASE", ".memory"), False


def diagnose(root: Path, config: dict) -> list[dict]:
    items: list[dict] = []

    def add(group: str, name: str, ok: bool | None, detail: str = "") -> None:
        items.append({"group": group, "item": name, "ok": ok, "detail": detail})

    # Git
    code, _ = run(["git", "rev-parse", "--show-toplevel"], root)
    is_repo = code == 0
    add("git", "repository", is_repo)
    base, has_pointer = memory_base(root)
    if is_repo:
        _, remotes = run(["git", "remote", "-v"], root)
        add("git", "remote", bool(remotes.strip()), remotes.split("\n")[0] if remotes.strip() else "none")
        ignored = run(["git", "check-ignore", "-q", base], root)[0] == 0
        _, tracked = run(["git", "ls-files", base], root)
        state = "ignored" if ignored else ("tracked" if tracked.strip() else "neither")
        add("git", f"{base}/ in Git", None, state)

    # Memory Tool
    memory = (root / base).is_dir() if base != "." else has_pointer
    add("memory-tool", "knowledge base", memory, f"base={base}" + ("" if has_pointer else " (no .memory-tool.yml)"))
    add("memory-tool", ".claude/guidelines.md", (root / ".claude/guidelines.md").is_file())
    for name in MT_SKILLS:
        add("memory-tool", f".claude/skills/{name}", (root / ".claude/skills" / name / "SKILL.md").is_file())
        add("codex", f".agents/skills/{name}", (root / ".agents/skills" / name / "SKILL.md").is_file())
    add("memory-tool", ".obsidian/ (vault: use a visible base)", None, "present" if (root / ".obsidian").is_dir() else "absent")

    # Goal Loop
    code, where = run(["goal-loop", "where"], root)
    source = ""
    if code == 0:
        try:
            source = json.loads(where).get("source", "")
        except json.JSONDecodeError:
            source = "unreadable"
    add("goal-loop", "journal (where)", source == "project", source or "goal-loop not runnable")
    judging = root / ".goal-loop/judging.json"
    judge = json.loads(judging.read_text(encoding="utf-8")).get("judge", "codex (default)") if judging.is_file() else "-"
    add("goal-loop", "judge", None, judge)
    add("goal-loop", ".claude/skills/goal-loop", (root / ".claude/skills/goal-loop/SKILL.md").is_file())
    add("codex", ".agents/skills/goal-loop", (root / ".agents/skills/goal-loop/SKILL.md").is_file())

    # Instruction files
    umbrella = config.get("umbrella", {}).get("path")
    is_umbrella = bool(umbrella) and same_path(umbrella, root)
    for name in ("CLAUDE.md", "AGENTS.md"):
        path = root / name
        if not path.is_file():
            add("instructions", name, False, "missing")
            continue
        text = path.read_text(encoding="utf-8")
        has_section = GOAL_LOOP_MARK in text
        detail = "goal-loop section" if has_section else ("umbrella: hand-written section expected" if is_umbrella else "no goal-loop section")
        if has_section and memory and "memory_tool context" not in text:
            detail += "; generated before Memory Tool (regenerate)"
        if name == "AGENTS.md" and not has_section and "CLAUDE.md" in text:
            detail = "points to CLAUDE.md"
        add("instructions", name, None, detail)
        add("instructions", f"{name} project-setup note", SETUP_MARK in text or detail == "points to CLAUDE.md")

    # User-level skills
    for name in GRILL_SKILLS:
        add("user-skills", f"~/.claude/skills/{name}", (Path.home() / ".claude/skills" / name / "SKILL.md").is_file(), "not needed when the plugin is installed")
        add("user-skills", f"$CODEX_HOME/skills/{name}", (codex_home() / "skills" / name / "SKILL.md").is_file())

    # CLIs
    for command in ("goal-loop", "goal-loop-judge", "minit"):
        found = shutil.which(command)
        add("cli", command, bool(found), found or "not on PATH")
    checkout = config.get("goal_loop", {}).get("dev_checkout")
    if checkout:
        exe = Path(checkout) / (".venv/Scripts/goal-loop.exe" if os.name == "nt" else ".venv/bin/goal-loop")
        if exe.is_file():
            same = run(["goal-loop", "help", "--all"], root)[1] == run([str(exe), "help", "--all"], root)[1]
            add("cli", "PATH goal-loop matches dev checkout", same)

    # Umbrella link
    if umbrella and not is_umbrella:
        code, links = run(["goal-loop", "aim-links"], Path(umbrella))
        needle = os.path.normcase(str(root.resolve())).replace("\\", "/")
        linked = code == 0 and needle in os.path.normcase(links).replace("\\\\", "/").replace("\\", "/")
        add("umbrella", f"linked from {umbrella}", linked)
    return items


def print_table(items: list[dict]) -> None:
    mark = {True: "ok", False: "MISSING", None: "-"}
    for row in items:
        print(f"{row['group']:<13} {mark[row['ok']]:<8} {row['item']:<42} {row['detail']}")


def trees_differ(diff: filecmp.dircmp) -> bool:
    if diff.left_only or diff.right_only or diff.diff_files or diff.funny_files:
        return True
    return any(trees_differ(sub) for sub in diff.subdirs.values())


def install_codex(force: bool) -> int:
    target = codex_home() / "skills"
    target.mkdir(parents=True, exist_ok=True)
    for skill in sorted(p for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").is_file()):
        dest = target / skill.name
        if dest.exists() and not force:
            if trees_differ(filecmp.dircmp(skill, dest, ignore=["__pycache__"])):
                print(f"kept     {dest} (differs; use --force to replace)")
            else:
                print(f"same     {dest}")
            continue
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill, dest, ignore=shutil.ignore_patterns("__pycache__"))
        print(f"copied   {dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("diagnose", help="read-only checks for one project")
    check.add_argument("root", nargs="?", default=".")
    check.add_argument("--json", action="store_true")
    codex = sub.add_parser("install-codex", help="copy this plugin's skills to $CODEX_HOME/skills")
    codex.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "install-codex":
        return install_codex(args.force)
    items = diagnose(Path(args.root).resolve(), load_config())
    if args.json:
        json.dump(items, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print_table(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
