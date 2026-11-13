---
name: grill-me
description: Interview the user until a plan, decision or idea is clear, one round of questions at a time. When the plan will be recorded in Goal Loop, also ask goal-loop-planning's questions and end with draft Goal Loop records.
disable-model-invocation: true
---

# Grill Me

The single entry point for plan interviews. `grilling` decides how to ask; `goal-loop-planning`, when it applies, decides what to ask and where the result goes.

## 1. How to ask

Load the `grilling` skill (in Claude Code it is `agent-workbench:grilling`) and follow it: the design tree, rounds of every question whose prerequisites are settled, a recommended answer for each, facts looked up by you and decisions put to the user, and its end condition.

While the rounds go on, do not record to the timeline (`m`), even when the project asks to record every activity: the interview counts as one activity, recorded at the end (section 4). If the project's rules explicitly make the interview rounds something to record, follow them instead.

## 2. Choose the mode

Decide from the subject. If it is unclear, make it the first question of the first round.

- **General:** a decision, a piece of writing, anything that will not be recorded in Goal Loop. Use `grilling` alone.
- **Goal Loop:** the plan will become Aims, criteria or Goals in this project's journal. This needs the `goal-loop-planning` skill (in `.claude/skills/` or `.agents/skills/`). If it is missing, say so, suggest running `project-setup`, and continue in general mode.

## 3. Goal Loop mode

Load `goal-loop-planning` and use it for what to ask:

- Start the tree with what that skill says to do when defining an Aim and asking about it: the result that changes, how we will know it is done, outside conditions, the stop condition. Choosing the approach, splitting, and each part's type come after. Refer to its parts by topic, not by section number; the skill keeps details in reference files that it names.
- Every recommended answer names the observation it rests on: a file, a log, a measurement, or the user's own words. Without one, say there is no observation and do not recommend a Contract for that part; it stays exploration. A recommendation without an observation is a guess, and a "yes" to a guess must not become a criterion.
- Look facts up the cheapest way first: read before you run, run before you build.
- Leave out questions that belong to later stages (diagnosis, a `not_satisfied` Verdict, a plateau). They are asked when that stage comes.

## 4. End

When the `grilling` end condition is met and the user confirms the shared understanding:

- **General:** summarize the decisions.
- **Goal Loop:** show the draft records as `goal-loop` commands with this agent's name as the actor: `aim-create`, the criteria `proposal-create` followed by `proposal-close --kind criteria`, and `goal-accept` for each part whose Contract can be written now. When the plan changes the criteria of an Aim that is still open, draft `aim-criteria-revise <aim-id> "<new criteria>" --supersedes <criteria proposal-id>` instead of a second criteria Proposal; the decision is the user's. Record nothing until the user approves, and follow the `goal-loop` skill for names and permissions.
- If the project keeps a timeline, ask once whether to record the settled decisions now, in one entry.
