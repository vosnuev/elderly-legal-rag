# AGENTS.md

## Repo Scope

This repository is a monorepo for the bootcamp project.

```txt
bootcamp-project/
├── frontend/   # 실제 프론트엔드
├── backend/    # 메인 백엔드 서비스
├── rag/        # RAG / 문서 파싱 / MCP 관련 작업
├── streamlit/  # Streamlit 기반 Python 프레임워크 프로젝트
├── docs_web/   # GitHub Pages 문서 웹
├── infra/      # Podman 등 인프라 실행/관리
├── docs/       # 프로젝트 문서
└── README.md   # 전체 프로젝트 설명
```

`.env.example` files are managed inside each service directory when needed. Do not add a root-level `.env.example` unless the team explicitly changes this policy.

## Shared Rules

- Read the relevant code, README, docs, and skill files before changing behavior.
- Prefer the smallest correct change.
- Keep unrelated changes in separate branches and separate pull requests.
- Do not edit generated build output unless explicitly requested.
- Maintain README files as Markdown documents.
- Update the root `README.md` and the relevant directory README when structure, setup, or run commands change.
- Do not commit secrets. Real `.env` files stay local only.
- If existing uncommitted changes appear to belong to someone else, do not overwrite them. Ask first.

## Project Skills

Project-scoped skills are committed under `.agents/skills/` and are the canonical shared skill source for this repo.
Keep skills for reusable agent workflows. Static repo structure rules live in this file, and README/documentation rules live in shared rules and the relevant docs.

Use these skills when relevant:

- `fastapi`: FastAPI API and Pydantic model best practices.
- `gh-cli`: GitHub CLI operations for repositories, issues, pull requests, Actions, and related workflows.
- `git-commit`: diff analysis, staging guidance, and commit message generation.
- `git-workflow`: branch, commit, and pull request decisions.
- `github-issues`: GitHub issue creation, updates, labels, metadata, dependencies, and workflows.
- `prd`: product requirements document creation and refinement.
- `shadcn`: shadcn/ui component usage, styling, customization, and project guidance.
- `uv-python`: repo-specific Python setup and dependency management with uv.
- `web-design-guidelines`: Vercel-sourced UI, UX, and accessibility review guidance.

Skill adapter directories for specific tools or agents are local-only unless the team explicitly approves committing them. Generated or personal directories such as `.claude/`, `.codex/`, `.gemini/`, `.factory/`, and `.opencode/` must not be committed.

## Git Workflow

This repo uses GitHub Flow.

- Do not work directly on `main` after the initial repository bootstrap unless the user explicitly requests it.
- Before starting work, check that the current branch matches the requested scope.
- Branch from the latest `main` for new work.
- Use short kebab-case branch names with a clear prefix:
  - `feature/<topic>`
  - `fix/<topic>`
  - `docs/<topic>`
  - `chore/<topic>`
  - `refactor/<topic>`
- If the task is unrelated to the current branch, move the work to a separate branch before implementation.
- If the user appears to be branching off while having uncommitted or unpushed work for a different feature, ask:

> 구현하려는 기능이 달라 보이는데, 혹시 push 한 다음에 진행하시는 건가요? 아니면 같은 기능 개발하시는건가요? 같은 기능이라면 동일한 branch 에서 진행해 주세요.

### Commit Rules

- Commit only after a logical unit of work is complete.
- Run the relevant basic checks before committing when they exist.
- Do not mix unrelated frontend, backend, RAG, Streamlit, infra, or docs changes in one commit.
- Avoid WIP commits unless the user asks for a checkpoint or handoff commit.
- Commit messages must be written in Korean.

### Atomic Commit Rules

- One commit should have one clear reason to exist.
- Split unrelated changes by service, domain, or workflow even when they are edited in the same session.
- Keep code, config, docs, and binary assets in separate commits unless the docs/assets directly explain the same change.
- Stage files intentionally. Review `git diff --staged` before committing.
- Do not sweep ignored files, local notes, generated output, or personal adapter config into a commit.
- If a task grows beyond the current branch scope, create or update a GitHub issue and move the extra work to a separate branch.

### Pull Request Rules

- Open PRs from a feature/fix/docs/chore/refactor branch into `main`.
- Keep PRs small enough to review.
- PR descriptions should include:
  - summary of changes
  - test/check results
  - affected directories
  - environment-variable or migration notes, if any
  - screenshots or screen recordings for UI changes, if useful
- Request review before merge. Do not self-merge unless the team explicitly allows it.

## Python Toolchain

Python projects in this repo must use `uv`.

- Use `uv init`, `uv add`, `uv sync`, `uv lock`, and `uv run`.
- Do not use `pip`, `pip3`, Poetry, or root-level `requirements.txt` for project dependency management.
- `backend/`, `rag/`, and `streamlit/` each manage their own `pyproject.toml`, `uv.lock`, `.python-version`, and `.venv/`.
- Keep virtual environments local. Do not commit `.venv/`.
- Do not run Python commands with the repository-root Python interpreter.
- For Python work, first move into the target project directory and use that directory's uv environment:
  - `cd backend && uv sync && uv run <command>`
  - `cd rag && uv sync && uv run <command>`
  - `cd streamlit && uv sync && uv run <command>`
- AI agents must choose the Python environment based on the file they are editing. A file under `backend/` uses `backend/.venv/bin/python`, a file under `rag/` uses `rag/.venv/bin/python`, and a file under `streamlit/` uses `streamlit/.venv/bin/python`.
- If a service `.venv/` does not exist, run `uv sync` inside that service directory before running Python, tests, or language-server-dependent commands.

## VS Code Workspace

- Open `SKN28-3rd-1Team.code-workspace` from the repository root when using VS Code.
- The workspace includes `backend/`, `rag/`, and `streamlit/` as separate folders so each folder can resolve `${workspaceFolder}/.venv/bin/python` relative to itself.
- When opening Python files, prefer the service folder entry in the workspace explorer, such as `backend/src/...`, `rag/src/...`, or `streamlit/src/...`, instead of the duplicated `repo-root/...` path.
- Service-local VS Code settings live in `backend/.vscode/settings.json`, `rag/.vscode/settings.json`, and `streamlit/.vscode/settings.json`.

## Tool And MCP Configuration

- Do not proactively inspect or modify global tool, MCP, or coding-agent configuration just because a matching tool might be useful.
- Check project configuration first.
- Only inspect or modify user-global configuration after the user explicitly asks for that setup.
- If a required tool or MCP server is missing, explain what needs to be installed or configured before changing global state.

## Detailed Guide

For the fuller workspace guide, see `docs/agent_workspace_guidelines.md`.


# additional notes:
for user specific rules, read instructions.md in project root
