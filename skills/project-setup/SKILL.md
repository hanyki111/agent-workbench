---
name: project-setup
description: Diagnose one project folder, fill in whatever is missing from the Goal Loop + Memory Tool setup (Memory Tool knowledge base, Goal Loop journal and skills, Codex copies, a minimal managed note), and tidy CLAUDE.md/AGENTS.md so they hold only always-on rules. Use when the user starts a new project, wants an existing project brought up to that setup, or wants its agent instructions cleaned up ("프로젝트 세팅해줘", "이 프로젝트에 goal loop랑 memory tool 붙여줘", "부족한 거 설치해줘", "CLAUDE.md 정리해줘", "set up this project").
---

# Project Setup

A project uses these pieces. This skill finds which ones are missing, asks, installs only those, and then tidies the
instruction files. A new project is the case where everything is missing, so the same procedure covers new and existing projects.

| Piece | What it provides | Installed by |
|:---|:---|:---|
| Memory Tool | knowledge base (`.memory/` by default), `.memory-tool.yml`, `.claude/guidelines.md`, `.claude/skills/mt-*` | `python -m memory_tool init` (alias `minit`) |
| Goal Loop | `.goal-loop/` journal, `goal-loop` and `goal-loop-planning` skills, a marked section in `CLAUDE.md` and `AGENTS.md` | `goal-loop project-init . --agents claude[,codex] [--skills-only] --judge <judge>` |
| grill-me / grilling | Plan interview skills | This plugin (Claude Code); `scripts/workbench.py install-codex` (Codex) |
| Managed note | Rules that apply only when the tools are used together | This skill, between `project-setup` markers |

Both tools stay standalone. This skill calls their own installers and never copies their templates, so a tool update reaches projects through the tool itself.

## Settings

`~/.agent-workbench.toml` holds personal settings; every key is optional (see `config.example.toml` in this plugin's repository):

- `[umbrella] path`, `parent_aim`: a folder whose Goal Loop journal plans several projects, and the Aim under which project Aims are linked.
- `[goal_loop] dev_checkout`: a Goal Loop development checkout to compare the PATH CLI against.

Never write personal paths or Aim IDs into this skill or into a project's files unless the user gives them.

## Rules

- Work on one project per run. Confirm the project root with the user before anything else (default: `git rev-parse --show-toplevel`, else the current folder).
- Diagnose first and change nothing until the user approves the specific actions.
- Never run `minit --force` or `minit --update-all`. They overwrite an existing knowledge base or templates.
- Text outside the `goal-loop` and `project-setup` markers belongs to the user. Change it only in step 3.6, and only as the diff the user approved.
- Show the exact diff before writing `CLAUDE.md`, `AGENTS.md` or `.gitignore`.
- Do not create Goal Loop Aims, Proposals or Goals on your own. Linking to the umbrella journal needs the user's approval for each record.

## 1. Diagnose

Run the read-only script from this skill's folder and read its table (`--json` for structured output):

```bash
python <this skill's folder>/scripts/workbench.py diagnose <project root>
```

Then check what the script cannot judge:

- **Goal Loop section:** the umbrella project keeps a hand-written Goal Loop section, so a missing generated section is expected there. An `AGENTS.md` that only points to `CLAUDE.md` and lists Codex differences is fine.
- **CLI version:** if the PATH `goal-loop` differs from the development checkout, check that the checkout's work is pushed (`git status -sb` shows no `ahead`), then suggest `python -m pipx reinstall goal-loop-tool`. `pipx upgrade` may do nothing because the version does not change.
- **Instruction files:** read `CLAUDE.md` and `AGENTS.md` whole and classify every block as in step 3.6. Report the line counts and how many lines each class holds.
- **Logging rule:** note whether the project's instructions require recording every activity (for example "record everything with `m`"). The managed note depends on it.

Report one table: item, current state, proposed action.

## 2. Ask

Ask everything in one message, with a recommended answer for each:

- Which proposed actions to apply.
- **The knowledge base and Git, every time:** usually exclude it, because the timeline is personal and a remote would publish it. A notes repository whose purpose is to keep it stays tracked. If it is already tracked, excluding it now does not remove history: say so.
- The judge for `--judge` (default `codex`; `claude` if Codex is not logged in).
- For an Obsidian vault, the base folder name (`--base memory` or `--base .`), since Obsidian hides dot folders.
- Whether the project is also used with Codex (copies to `.agents/skills/`, an `AGENTS.md`).
- Whether to tidy `CLAUDE.md` and `AGENTS.md` (step 3.6). Recommend it when they hold usage, history or duplicates.
- Whether to link the project to the umbrella journal, when one is configured.

## 3. Apply, in this order

1. **Memory Tool** (if missing): `python -m memory_tool init [--base <name>]`. It must run before Goal Loop so that the Goal Loop section includes the Memory Tool steps.
2. **`.gitignore`:** add the knowledge base folder only if the user chose to exclude it.
3. **Goal Loop:** `goal-loop project-init . --agents claude[,codex] --judge <judge>`.
   - Use the generated section by default: it is short and the tool keeps it current. Add `--skills-only` only in the umbrella project, or when the user keeps a hand-written Goal Loop section. With `--skills-only`, check that the hand-written text still has the three rules the command names in its `instructions` field (the agent's name, never recording as `user`, the judge per agent).
   - Re-running is safe: only the text inside its markers changes. A skill file whose content differs is `kept`, not replaced. When the kept file is an older copy of the tool's template (nobody edited it), ask, then delete it and run the command again.
   - Report every `kept` and `warnings` entry.
4. **Codex** (if used): copy each `.claude/skills/mt-*/` to `.agents/skills/mt-*/`, skipping a destination that differs and reporting it. Run `python <this skill's folder>/scripts/workbench.py install-codex` once per machine for the user-level skills (`--force` replaces copies that differ).
5. **Managed note:** add it only for rules the project does not already have. Today it holds one rule, so add it only when the project requires recording every activity; otherwise grilling rounds are already outside what gets recorded, and the note is noise. If the markers exist but the rule no longer applies, propose removing the block.

   ```markdown
   <!-- project-setup:begin (project-setup 스킬이 관리하는 절입니다. 표지 안을 고치면 다시 실행할 때 바뀝니다) -->
   ## 질문 세션

   - `grill-me`(`grilling`)로 계획을 검증하는 동안에는 질문 라운드마다 타임라인에 기록하지 않는다. 사용자가 합의를 확인하면, 정해진 결정을 한 번에 타임라인에 기록할지 묻는다.
   <!-- project-setup:end -->
   ```

   Place it after the Goal Loop section and match the heading level to the surrounding text. When `AGENTS.md` only points to `CLAUDE.md`, the block goes in `CLAUDE.md` alone.

6. **Tidy `CLAUDE.md` and `AGENTS.md`** (if approved). These files load in every session, so they hold only what must apply without a request. Classify every block:

   | Class | Example | Action |
   |:---|:---|:---|
   | Always-on rule | principles, the agent's name, never recording as `user`, judge separation, "record every activity", which interpreter to use | Keep, one line each; name the skill that holds the how-to |
   | Project fact | what the project is, folder layout, an umbrella's Aim map | Keep, short |
   | Usage or procedure | command lists, option details, step-by-step workflows | Delete when an installed skill already holds it (name the skill); otherwise move to `docs/` or propose a project skill |
   | Design notes or history | how a mechanism works inside, why it changed, goal IDs of past fixes | Move to `docs/` |
   | Duplicate | the same rule in the tool's generated section, or in both files | Keep one copy, preferring the tool's section |
   | Stale | text that no longer matches the project | Point it out; the user rewrites or deletes it |

   - Show a table of every removed or moved block and its destination, then the full diff. Nothing is removed without a destination unless an installed skill already holds it, and you say which.
   - When `AGENTS.md` repeats `CLAUDE.md`, replace it with a short file that points to `CLAUDE.md` and lists only the Codex differences: record as `codex`; skills are in `.agents/skills/`; Codex's own work is judged with `--judge claude`.
   - Keep the user's wording in what stays. Do not rewrite sentences that are kept.
   - Moving text to `docs/` creates files: name them in the diff.
   - If another session is working in the same repository (uncommitted changes to these files), stop and say so instead of editing.

7. **Umbrella link** (if configured and approved): the project needs an Aim of its own first; if it has none, stop here and tell the user to link later. Otherwise, with approval for each command, run inside the umbrella folder:

   ```bash
   goal-loop aim-create "<project name>" --parent <parent_aim>
   goal-loop aim-link-add <new-aim-id> --project <project root> --external-aim <project aim-id> --actor claude
   ```

8. **Timeline:** if the project has Memory Tool, propose one line such as `m "project-setup: Memory Tool, Goal Loop 설치; 지식 폴더는 Git에서 제외"` and record it only after the user agrees.

## 4. Verify

Run the diagnosis again and show the final table, including the new line counts of `CLAUDE.md` and `AGENTS.md`. Print every ID that Goal Loop returned. List anything left undone and why.

## Updating grilling

`grilling` is vendored unchanged from `mattpocock/skills` (MIT) at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`; update it with its `agents/openai.yaml` and `LICENSE`. `grill-me` is this plugin's own entry point (see `THIRD_PARTY.md`); do not replace it with the upstream one-liner. Do not add `grill-with-docs` or `wayfinder`: their ADR/glossary files and effort maps overlap Memory Tool documents and Goal Loop Aims.
