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
MT_SKILLS = ("mt-record", "mt-write", "mt-publish", "mt-master-module")
GRILL_SKILLS = ("grill-me", "grilling")
GOAL_LOOP_SKILLS = ("goal-loop", "goal-loop-planning")
GOAL_LOOP_MARK = "<!-- goal-loop:begin"
SETUP_MARK = "<!-- project-setup:begin"
QUESTION_RULE = "is one activity"  # mt-record (memory_tool 1.10.1+): a question session counts as one activity


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


def plugin_installed() -> bool:
    """Whether Claude Code lists this plugin as installed for the user."""
    path = Path.home() / ".claude/plugins/installed_plugins.json"
    try:
        return "agent-workbench@" in path.read_text(encoding="utf-8")
    except OSError:
        return False


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
    if (root / ".claude/guidelines.md").is_file():
        add("memory-tool", ".claude/guidelines.md", False, "left by an older version; minit --update-all sets it aside")
    record_skill = root / ".claude/skills/mt-record/SKILL.md"
    has_question_rule = record_skill.is_file() and QUESTION_RULE in record_skill.read_text(encoding="utf-8")
    if record_skill.is_file() and not has_question_rule:
        add("memory-tool", "mt-record question-session rule", False, "older than memory_tool 1.10.1; minit --update-all")
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
    for name in GOAL_LOOP_SKILLS:
        add("goal-loop", f".claude/skills/{name}", (root / ".claude/skills" / name / "SKILL.md").is_file())
        add("codex", f".agents/skills/{name}", (root / ".agents/skills" / name / "SKILL.md").is_file())

    # Instruction files: AGENTS.md is the source, CLAUDE.md imports it
    umbrella = config.get("umbrella", {}).get("path")
    is_umbrella = bool(umbrella) and same_path(umbrella, root)
    texts = {name: (root / name).read_text(encoding="utf-8") for name in ("CLAUDE.md", "AGENTS.md") if (root / name).is_file()}
    for name in ("CLAUDE.md", "AGENTS.md"):
        if name not in texts:
            add("instructions", name, False, "missing")
            continue
        add("instructions", name, None, f"{len(texts[name].splitlines())} lines")
    claude, agents = texts.get("CLAUDE.md", ""), texts.get("AGENTS.md", "")
    imports = any(line.strip() == "@AGENTS.md" for line in claude.splitlines())
    add("instructions", "CLAUDE.md imports @AGENTS.md", imports, "" if imports else "layout: AGENTS.md should be the source")
    generated = [name for name, text in texts.items() if GOAL_LOOP_MARK in text]
    if generated:
        reason = "duplicates the umbrella's hand-written section" if is_umbrella else "names one agent; use --skills-only and the shared rules"
        add("instructions", "generated goal-loop section", False, f"in {', '.join(generated)}: {reason}")
    if "guidelines.md" in claude + agents and not (root / ".claude/guidelines.md").is_file():
        add("instructions", "reference to .claude/guidelines.md", False, "stale: the file is retired; usage is in mt-record")
    if SETUP_MARK in claude + agents:
        detail = "retire: mt-record has the rule" if has_question_rule else "retire after minit --update-all (mt-record lacks the rule)"
        add("instructions", "project-setup note", False, detail)

    # User-level skills
    plugin = plugin_installed()
    for name in GRILL_SKILLS:
        user_copy = (Path.home() / ".claude/skills" / name / "SKILL.md").is_file()
        detail = "from the agent-workbench plugin" if plugin else ""
        if plugin and user_copy:
            detail += "; ~/.claude/skills copy is a duplicate"
        add("user-skills", f"Claude Code: {name}", plugin or user_copy, detail or "~/.claude/skills")
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
