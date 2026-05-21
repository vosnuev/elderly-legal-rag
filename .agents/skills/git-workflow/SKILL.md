---
name: git-workflow
description: Use this skill for branch selection, commit timing, commit message style, and pull request preparation in this repository.
---

# Git Workflow Skill

This repository uses GitHub Flow.

## Before Work

1. Check the current branch.
2. Check the working tree.
3. Confirm that the requested task matches the current branch scope.

## Branching

Do not work directly on `main` after initial bootstrap unless the user explicitly asks.

Use branch names like:

- `feature/<topic>`
- `fix/<topic>`
- `docs/<topic>`
- `chore/<topic>`
- `refactor/<topic>`

Create a new branch when the task is unrelated to the current branch or current diff.

If the user appears to be branching off while uncommitted or unpushed work exists for another feature, ask:

> 구현하려는 기능이 달라 보이는데, 혹시 push 한 다음에 진행하시는 건가요? 아니면 같은 기능 개발하시는건가요? 같은 기능이라면 동일한 branch 에서 진행해 주세요.

## Commits

Commit only after a logical unit of work is complete and relevant checks/docs are updated.

Rules:

- Commit messages must be written in Korean.
- Do not mix unrelated changes in one commit.
- Do not commit secrets, `.env`, virtual environments, generated build output, or personal agent config.
- Avoid WIP commits unless the user requests a checkpoint or handoff.

## Pull Requests

PRs should target `main` and include:

- summary;
- test/check results;
- affected directories;
- environment-variable or migration notes;
- screenshots/recordings for UI changes when useful.
