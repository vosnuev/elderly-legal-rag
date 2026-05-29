# Project Skills

This directory is the canonical shared skill source for this repository.

## Skills

- `fastapi/` — FastAPI API and Pydantic model best practices.
- `gh-cli/` — GitHub CLI operations for repositories, issues, pull requests, Actions, and related workflows.
- `git-commit/` — diff analysis, staging guidance, and commit message generation.
- `git-workflow/` — branch, commit, and pull request decision rules.
- `github-issues/` — GitHub issue creation, updates, labels, metadata, dependencies, and workflows.
- `prd/` — product requirements document creation and refinement.
- `shadcn/` — shadcn/ui component usage, styling, customization, and project guidance.
- `uv-python/` — Python setup and dependency management with uv.
- `web-design-guidelines/` — UI, UX, and accessibility review guidance.

## Source Notes

- `web-design-guidelines/` follows Vercel's Web Interface Guidelines source.
- `uv-python/` stays repo-scoped. On 2026-05-22, `npx skills find "uv python"` returned `mindrally/skills@python-uv` as the closest match with 499 installs, but no official or high-install replacement was selected.

## Rules

- Keep reusable agent guidance here instead of duplicating it in personal tool configs.
- Keep static repo structure and README maintenance rules in `AGENTS.md`, directory READMEs, and `docs/` instead of duplicating them as skills.
- If an agent requires generated adapters, create them locally and do not commit them unless the team explicitly approves.
- Update `AGENTS.md` when adding, renaming, or removing shared skills.
