---
name: project-setup
description: Diagnose one project folder, fill in whatever is missing from the Goal Loop + Memory Tool setup (Memory Tool knowledge base and skills, Goal Loop journal and skills), and tidy the agent instructions into one AGENTS.md that CLAUDE.md imports, holding only always-on rules. Use when the user starts a new project, wants an existing project brought up to that setup, or wants its agent instructions cleaned up ("프로젝트 세팅해줘", "이 프로젝트에 goal loop랑 memory tool 붙여줘", "부족한 거 설치해줘", "CLAUDE.md 정리해줘", "set up this project").
---

# Project Setup

A project uses these pieces. This skill finds which ones are missing, asks, installs only those, and then tidies the
instruction files. A new project is the case where everything is missing, so the same procedure covers new and existing projects.

| Piece | What it provides | Installed or updated by |
|:---|:---|:---|
| Memory Tool | knowledge base (`.memory/` by default), `.memory-tool.yml`, `mt-*` skills in `.claude/skills/` and `.agents/skills/`, `<base>/templates/CLAUDE.md.template` | `python -m memory_tool init` (alias `minit`); `minit --update-all` refreshes skills in an existing project |
| Goal Loop | `.goal-loop/` journal, `goal-loop` and `goal-loop-planning` skills in `.claude/skills/` and `.agents/skills/` | `goal-loop project-init . --agents claude,codex --skills-only --judge <judge>` |
| grill-me / grilling | Plan interview skills | This plugin (Claude Code); `scripts/workbench.py install-codex` (Codex) |
| Instructions | `AGENTS.md` with the always-on rules; `CLAUDE.md` that imports it | This skill (step 3.5) |

Both tools stay standalone. This skill calls their installers and reads their templates in the project; it never keeps copies of them, so a tool update reaches projects through the tool itself.

## Instruction layout

`AGENTS.md` is the single source: Codex reads it directly and Claude Code reads it through `@AGENTS.md`. Both files load in every session, so they hold only what must apply without a request; how to use a tool lives in its skill.

- `AGENTS.md`: the project's own rules and facts, the Memory Tool rules, and the shared Goal Loop rules. The shared rules name both agents in one place (Claude Code records as `claude`, Codex as `codex`; each one's work goes to its own judge). There is no agent-only section, so neither agent reads a rule meant for the other.
- `CLAUDE.md`: `@AGENTS.md` and nothing else, unless a rule really is Claude-only.
- Goal Loop is installed with `--skills-only`, because its generated section names one agent and would reach Claude through the import. The command's `judges_by_agent` gives the judge for each agent.

## Settings

`~/.agent-workbench.toml` holds personal settings; every key is optional (see `config.example.toml` in this plugin's repository):

- `[umbrella] path`, `parent_aim`: a folder whose Goal Loop journal plans several projects, and the Aim under which project Aims are linked.
- `[goal_loop] dev_checkout`: a Goal Loop development checkout to compare the PATH CLI against.
- `[goal_loop] package_dir`: the installed `goal_loop_tool` package folder, when it is not in the pipx venv the script looks in.

Never write personal paths or Aim IDs into this skill or into a project's files unless the user gives them.

## Rules

- Work on one project per run. Confirm the project root with the user before anything else (default: `git rev-parse --show-toplevel`, else the current folder).
- Diagnose first and change nothing until the user approves the specific actions.
- Never run `minit --force`: it overwrites an existing knowledge base. `minit --update-all` replaces the `mt-*` skills and sets aside an old `.claude/guidelines.md` with a backup; run it only after saying so and getting approval.
- Text outside the `goal-loop` and `project-setup` markers belongs to the user. Change it only in step 3.5, and only as the diff the user approved.
- Show the exact diff before writing `CLAUDE.md`, `AGENTS.md` or `.gitignore`.
- Do not create Goal Loop Aims, Proposals or Goals on your own. Linking to the umbrella journal needs the user's approval for each record.
- If another session is changing the same files (uncommitted changes you did not make), stop and say so instead of editing.

## 1. Diagnose

Run the read-only script from this skill's folder and read its table (`--json` for structured output):

```bash
python <this skill's folder>/scripts/workbench.py diagnose <project root>
```

Then check what the script cannot judge:

- **Skill copies:** the `copies` rows compare each project copy with the installed tool's template. A copy that differs is either older or edited by someone. Check the file's history (`git log -p -- <file>`): if only tool updates touched it, propose refreshing it (Memory Tool: `minit --update-all`; Goal Loop: delete the copy and run `project-init` again). If someone edited it, show the difference and let the user choose.
- **CLI version:** if the PATH `goal-loop` differs from the development checkout, check that the checkout's work is pushed (`git status -sb` shows no `ahead`), then suggest `python -m pipx reinstall goal-loop-tool`. `pipx upgrade` may do nothing because the version does not change.
- **Instruction files:** read `CLAUDE.md` and `AGENTS.md` whole and classify every block as in step 3.5. Report the line counts, the layout (which file is the source, whether `CLAUDE.md` imports `AGENTS.md`), and how many lines each class holds.

Report one table: item, current state, proposed action.

## 2. Ask

Ask everything in one message, with a recommended answer for each:

- Which proposed actions to apply.
- **The knowledge base and Git, every time:** usually exclude it, because the timeline is personal and a remote would publish it. A notes repository whose purpose is to keep it stays tracked. If it is already tracked, excluding it now does not remove history: say so.
- The judge for `--judge` (default `codex`; `claude` if Codex is not logged in).
- For an Obsidian vault, the base folder name (`--base memory` or `--base .`), since Obsidian hides dot folders.
- Whether to tidy the instruction files into the layout above (step 3.5). Recommend it when they hold usage, history or duplicates, or use another layout.
- Whether to link the project to the umbrella journal, when one is configured.

## 3. Apply, in this order

1. **Memory Tool:** if missing, `python -m memory_tool init [--base <name>]`. If present but its skills are missing or old (no `mt-record`, an `mt-record` without the question-session rule from memory_tool 1.10.1, or a `.claude/guidelines.md` left over), `python -m memory_tool init --update-all` after approval. Either way the skills land in `.claude/skills/` and `.agents/skills/`.
2. **`.gitignore`:** add the knowledge base folder only if the user chose to exclude it.
3. **Goal Loop:** `goal-loop project-init . --agents claude,codex --skills-only --judge <judge>`. Keep its `judges_by_agent` for step 3.5. A skill file whose content differs is `kept`, not replaced; when the kept file is an older copy of the tool's template (nobody edited it), ask, then delete it and run the command again. Report every `kept` and `warnings` entry.
   If a generated `goal-loop` section is already in `CLAUDE.md` or `AGENTS.md`, step 3.5 replaces it with the shared rules; do not leave both.
4. **Retire the managed note:** earlier versions of this skill added a `project-setup` block (no recording during question rounds) to `AGENTS.md` or `CLAUDE.md`. That rule now lives in `mt-record` (memory_tool 1.10.1 and later) and in `grill-me`, so no new block is added. If a block exists and the project's `mt-record` copy has the rule, propose removing the block. If the copy is older, propose `python -m memory_tool init --update-all` first (step 3.1), then removing it; removing it before that would leave the project without the rule.

5. **Tidy into the layout** (if approved). Build `AGENTS.md` from:
   - the project's own rules and facts that are already there (kept in the user's wording);
   - the Memory Tool rules from `<base>/templates/CLAUDE.md.template` (its `## Memory Tool` section), adjusted where the project already says otherwise, such as its recording rule;
   - the shared Goal Loop rules below, with `<memory step>` replaced by the Memory Tool session-start step when the project has Memory Tool, and the judges taken from `judges_by_agent`.

   ```markdown
   ## Goal Loop

   이 프로젝트의 작업은 Goal Loop 기록(`.goal-loop/`)으로 추적한다. 명령과 절차는 `goal-loop` 스킬(Claude Code는 `.claude/skills/`, Codex는 `.agents/skills/`)과 `goal-loop guide`에 있다.
   Aim을 만들거나 나누기 전, 접근을 고르기 전, 기준과 Contract를 쓰기 전, 불합격이 나온 뒤에는 `goal-loop-planning` 스킬을 따른다.

   - 세션 시작: <memory step> `goal-loop where`(`source: project` 확인), `goal-loop next`, `goal-loop status`로 열린 Aim, 실행 중인 Attempt, 검증 대기를 요약한다.
   - 기록 이름은 Claude Code가 `claude`, Codex가 `codex`이다. `user` 이름으로는 아무것도 기록하지 않는다. 종료, 일시 중지와 재개, 보류, 검토 해소는 사용자가 정한다.
   - Verdict와 Aim 평가는 직접 기록하지 않고 실행하지 않은 쪽에 맡긴다: `goal-loop verification-begin <goal-id> <attempt-id>` 뒤, Claude가 실행한 일은 `goal-loop-judge --judge <judge for claude> goal <goal-id>`, Codex가 실행한 일은 `--judge <judge for codex>`로 맡긴다. Aim은 `aim <aim-id>`.
   - 판정에 동의하지 않으면 의견을 Evidence로 남기고 사용자에게 알린다. 다른 결과를 얻으려고 판정을 다시 실행하지 않는다.
   ```

   And `CLAUDE.md`:

   ```markdown
   @AGENTS.md
   ```

   An umbrella project keeps its hand-written Goal Loop section (its Aim map, links and judging rules) instead of the shared block, but still follows the layout.

   Classify every existing block before moving it:

   | Class | Example | Action |
   |:---|:---|:---|
   | Always-on rule | principles, the agent's name, never recording as `user`, judge separation, the recording rule, which interpreter to use | Keep, one line each; name the skill that holds the how-to |
   | Project fact | what the project is, folder layout, an umbrella's Aim map | Keep, short |
   | Usage or procedure | command lists, option details, step-by-step workflows | Delete when an installed skill already holds it (name the skill, for example `mt-record` for `m`/`ms`/`mcontext`); otherwise move to `docs/` or propose a project skill |
   | Design notes or history | how a mechanism works inside, why it changed, goal IDs of past fixes | Move to `docs/` |
   | Duplicate | a rule in both files, or a generated section next to a hand-written one | Keep one copy |
   | Stale | references to files that no longer exist (such as a retired `.claude/guidelines.md`), text that no longer matches the project | Point it out; the user rewrites or deletes it |

   - Show a table of every removed or moved block and its destination, then the full diff of both files. Nothing is removed without a destination unless an installed skill already holds it, and you say which.
   - Keep the user's wording in what stays. Do not rewrite sentences that are kept.
   - Moving text to `docs/` creates files: name them in the diff.

6. **Codex user-level skills:** run `python <this skill's folder>/scripts/workbench.py install-codex` once per machine (`--force` replaces copies that differ).
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
