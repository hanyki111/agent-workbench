---
name: project-setup
description: Diagnose one project folder and fill in whatever is missing from the Goal Loop + Memory Tool setup - Memory Tool knowledge base, Goal Loop journal and skills, the grill-me/grilling skills, Codex copies, and a minimal managed note in CLAUDE.md/AGENTS.md. Use when the user starts a new project or wants an existing project brought up to that setup ("프로젝트 세팅해줘", "이 프로젝트에 goal loop랑 memory tool 붙여줘", "부족한 거 설치해줘", "set up this project").
---

# Project Setup

A project uses four pieces. This skill finds which ones are missing, asks, and installs only those.
A new project is the case where all four are missing, so the same procedure covers new and existing projects.

| Piece | What it provides | Installed by |
|:---|:---|:---|
| Memory Tool | knowledge base (`.memory/` by default), `.memory-tool.yml`, `.claude/guidelines.md`, `.claude/skills/mt-*` | `python -m memory_tool init` (alias `minit`) |
| Goal Loop | `.goal-loop/` journal, `goal-loop` skill, optional marked section in `CLAUDE.md` and `AGENTS.md` | `goal-loop project-init . --agents claude,codex --judge <judge>` |
| grill-me / grilling | Plan interview skills | This plugin (Claude Code); `scripts/workbench.py install-codex` (Codex) |
| Managed note | The few rules that apply only when the tools are used together | This skill, between `project-setup` markers |

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
- Text outside the `goal-loop` and `project-setup` markers belongs to the user. Do not rewrite it. If something there contradicts the setup, point it out and let the user decide.
- Show the exact diff before writing `CLAUDE.md`, `AGENTS.md` or `.gitignore`.
- Keep `CLAUDE.md` and `AGENTS.md` small: they hold only rules that apply without a request. Usage belongs in skills.
- Do not create Goal Loop Aims, Proposals or Goals on your own. Linking to the umbrella journal needs the user's approval for each record.

## 1. Diagnose

Run the read-only script from this skill's folder and read its table (`--json` for structured output):

```bash
python <this skill's folder>/scripts/workbench.py diagnose <project root>
```

Then check what the script cannot judge:

- **Goal Loop section:** if the umbrella journal lives in this project, its hand-written Goal Loop section is expected and no generated section is needed. An `AGENTS.md` that only points to `CLAUDE.md` and lists Codex differences is fine.
- **CLI version:** if the PATH `goal-loop` differs from the development checkout, check that the checkout's work is pushed (`git status -sb` shows no `ahead`), then suggest `python -m pipx reinstall goal-loop-tool`. `pipx upgrade` may do nothing because the version does not change.
- **Conflicts:** read `CLAUDE.md` and `AGENTS.md` for text that contradicts the managed note or repeats a tool's instructions.

Report one table: item, current state, proposed action.

## 2. Ask

Ask everything in one message, with a recommended answer for each:

- Which proposed actions to apply.
- **The knowledge base and Git, every time:** usually exclude it, because the timeline is personal and a remote would publish it. A notes repository whose purpose is to keep it stays tracked. If it is already tracked, excluding it now does not remove history: say so.
- The judge for `--judge` (default `codex`; `claude` if Codex is not logged in).
- For an Obsidian vault, the base folder name (`--base memory` or `--base .`), since Obsidian hides dot folders.
- Whether the project is also used with Codex (copies to `.agents/skills/`, an `AGENTS.md`).
- Whether to link the project to the umbrella journal, when one is configured.

## 3. Apply, in this order

1. **Memory Tool** (if missing): `python -m memory_tool init [--base <name>]`. It must run before Goal Loop so that the Goal Loop section includes the Memory Tool steps.
2. **`.gitignore`:** add the knowledge base folder only if the user chose to exclude it.
3. **Goal Loop:** `goal-loop project-init . --agents claude[,codex] --judge <judge>`. Re-running is safe: only the text inside its markers changes, and differing skill files are kept (`kept` in the result). Report any `kept` or `warnings`. In the umbrella project, do not run it with `--agents`; copy the installed package's `goal_loop_tool/agent_files/goal-loop-SKILL.md` to `.claude/skills/goal-loop/` (and `.agents/skills/goal-loop/` for Codex) instead.
4. **Codex** (if used): copy each `.claude/skills/mt-*/` to `.agents/skills/mt-*/`, skipping a destination that differs and reporting it. When the project already has a `CLAUDE.md`, `AGENTS.md` can be a short file that points to it and lists only the Codex differences: record as `codex`; skills are in `.agents/skills/`; Codex's own work is judged with `--judge claude`. Run `python <this skill's folder>/scripts/workbench.py install-codex` once per machine for the user-level skills.
5. **Managed note:** add this block to `CLAUDE.md`, right after the Goal Loop section if there is one. If markers already exist, replace only what is between them. Match the heading level to the surrounding text. Include only the bullets the file does not already say elsewhere: drop the first when the file already points to `.claude/guidelines.md` or there is no Memory Tool; drop the third when the `goal-loop` skill is installed (its guardrails already require approval) or there is no Goal Loop. When `AGENTS.md` only points to `CLAUDE.md`, the block goes in `CLAUDE.md` alone.

   ```markdown
   <!-- project-setup:begin (project-setup 스킬이 관리하는 절입니다. 표지 안을 고치면 다시 실행할 때 바뀝니다) -->
   ## 질문 세션과 기록

   - Memory Tool 사용법은 `.claude/guidelines.md`에 있다.
   - `grill-me`(`grilling`)로 계획을 검증하는 동안에는 질문 라운드마다 타임라인에 기록하지 않는다. 사용자가 합의를 확인하면, 정해진 결정을 한 번에 타임라인에 기록할지 묻는다.
   - 정해진 결정을 Goal Loop의 Aim, Proposal, Goal로 옮기는 일은 사용자가 승인한 뒤에만 한다.
   <!-- project-setup:end -->
   ```

6. **Umbrella link** (if configured and approved): the project needs an Aim of its own first; if it has none, stop here and tell the user to link later. Otherwise, with approval for each command, run inside the umbrella folder:

   ```bash
   goal-loop aim-create "<project name>" --parent <parent_aim>
   goal-loop aim-link-add <new-aim-id> --project <project root> --external-aim <project aim-id> --actor claude
   ```

7. **Timeline:** if the project has Memory Tool, propose one line such as `m "project-setup: Memory Tool, Goal Loop 설치; 지식 폴더는 Git에서 제외"` and record it only after the user agrees.

## 4. Verify

Run the diagnosis again and show the final table. Print every ID that Goal Loop returned. List anything left undone and why.

## Updating grill-me and grilling

They are vendored from `mattpocock/skills` (MIT) at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`; see `THIRD_PARTY.md` in this plugin's repository. `grill-me` only calls `grilling`, so update both together, with `agents/openai.yaml` and `LICENSE`. Do not add `grill-with-docs` or `wayfinder`: their ADR/glossary files and effort maps overlap Memory Tool documents and Goal Loop Aims.
