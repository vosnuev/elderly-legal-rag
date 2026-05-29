# Agent Workspace Guidelines

This document expands the shared rules in `AGENTS.md`.

## Start-of-Work Checklist

1. Check the current branch and working tree.
2. Confirm the task matches the current branch scope.
3. Read the relevant directory README and matching files under `.agents/skills/`.
4. Make the smallest correct change.
5. Run relevant checks when available.
6. Update documentation if setup, commands, structure, or behavior changed.

## Branch Decision Boundary

Create or switch to a separate branch when:

- the requested work is unrelated to the current branch name or current diff;
- the change affects a different major directory for a different purpose;
- the work would make the current PR too broad;
- there are existing uncommitted changes that appear to belong to another task.

Stay on the same branch when:

- the work directly completes or fixes the current branch's feature;
- the change is a small follow-up requested during the same review/context;
- documentation updates explain the same code change.

## Commit Decision Boundary

Commit when:

- a coherent unit of work is complete;
- relevant checks have passed or the failure is documented;
- docs and examples are updated when needed.

Do not commit when:

- the work is partial and the user did not request a checkpoint;
- unrelated changes are mixed together;
- local secrets, `.env`, virtual environments, build output, or personal agent config are included.

## Atomic Commit Checklist

Before committing, confirm:

- the staged diff has one purpose;
- the commit can be reviewed without unrelated context;
- frontend, backend, RAG, Streamlit, infra, and docs-only work are split when they are independent;
- docs or assets are staged with code only when they explain the same change;
- ignored files, local notes, generated output, and personal adapter config are not staged.

If the remaining work is useful but out of branch scope, capture it in a GitHub issue instead of expanding the commit.

## Pull Request Checklist

Each PR should include:

- what changed;
- why it changed;
- how it was tested;
- affected directories;
- environment-variable changes, if any;
- screenshots or recordings for UI changes, if useful.

## Tool Configuration Boundary

Project configuration can be inspected when it is part of the task. User-global configuration, MCP server setup, and personal coding-agent configuration require explicit user approval before inspection or modification.
