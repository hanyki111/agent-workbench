# agent-workbench

[Goal Loop](https://github.com/hanyki111/goal-loop)와 [Memory Tool](https://github.com/hanyki111/memory_tool)을 함께 쓰는 프로젝트를 설정하고 점검하는 Claude Code plugin입니다.
두 도구는 각자 혼자 동작합니다. 이 저장소는 두 도구를 함께 쓸 때에만 필요한 것을 맡습니다: 설치 순서, 빠진 부분의 진단, Codex용 스킬 복사, 그리고 `CLAUDE.md`·`AGENTS.md`에 넣는 최소한의 규칙.

## 들어 있는 스킬

| 스킬 | 하는 일 |
|:---|:---|
| `project-setup` | 프로젝트 하나를 진단하고, 사용자가 승인한 항목만 설치합니다. 새 프로젝트와 기존 프로젝트에 같은 절차를 씁니다. |
| `grill-me` | 계획이나 결정을 질문으로 검증하는 입구입니다(`/agent-workbench:grill-me`). Goal Loop에 기록할 계획이면 `goal-loop-planning`의 질문을 함께 쓰고, 끝에 Goal Loop 기록 초안을 보여 줍니다. |
| `grilling` | `grill-me`가 따르는 질문 방식입니다. [mattpocock/skills](https://github.com/mattpocock/skills)의 원본을 그대로 포함합니다(MIT, [THIRD_PARTY.md](THIRD_PARTY.md)). |

## 요구 사항

- Python 3.11 이상
- [Goal Loop](https://github.com/hanyki111/goal-loop): `pipx install git+https://github.com/hanyki111/goal-loop`
- [Memory Tool](https://github.com/hanyki111/memory_tool): 저장소의 설치 안내를 따릅니다.
- Codex를 함께 쓸 때: Codex CLI

## 설치

Claude Code에서:

```text
/plugin marketplace add hanyki111/agent-workbench
/plugin install agent-workbench@agent-workbench
```

Codex에서도 스킬을 쓰려면 한 번 실행합니다(`$CODEX_HOME/skills`, 기본 `~/.codex/skills`에 복사합니다):

```bash
python skills/project-setup/scripts/workbench.py install-codex
```

개인 설정(거시 저널 위치 등)이 필요하면 [config.example.toml](config.example.toml)을 `~/.agent-workbench.toml`로 복사해 고칩니다. 설정이 없어도 동작합니다.

## 사용

프로젝트 폴더에서 Claude Code를 열고 `/agent-workbench:project-setup`을 실행합니다. 진단 결과를 보여 준 뒤 무엇을 설치할지 묻고, 승인한 항목만 바꿉니다.
진단만 따로 보려면:

```bash
python skills/project-setup/scripts/workbench.py diagnose <프로젝트 폴더>
```

## 설계 원칙

- **도구는 각자 혼자 동작합니다.** 이 plugin은 두 도구의 설치 명령을 부를 뿐, 도구의 템플릿을 복사해 두지 않습니다.
- **지침 파일은 작게 둡니다.** `CLAUDE.md`와 `AGENTS.md`에는 요청이 없어도 지켜야 하는 규칙만 두고, 사용법은 스킬에 둡니다.
- **바꾸기 전에 묻습니다.** 진단은 읽기만 하고, 지침 파일을 고칠 때에는 diff를 먼저 보여 줍니다.

## 라이선스

[Apache License 2.0](LICENSE)으로 배포합니다. 저작권 표기는 [NOTICE](NOTICE)에 있습니다.
포함한 `grilling` 스킬은 MIT 라이선스를 따릅니다([THIRD_PARTY.md](THIRD_PARTY.md)).
