---
name: readme-docs
description: Use this skill when creating or changing README files, setup instructions, or project documentation.
---

# README / Docs Skill

## Rules

- README files must be valid Markdown.
- Update the root `README.md` when top-level structure, setup policy, or shared commands change.
- Update the relevant directory README when local setup, run, build, test, or environment behavior changes.
- Keep instructions copy-pasteable.
- Document environment-variable names in `.env.example`, but never include real secrets.

## Minimum README Sections For Services

When a service becomes active, its README should include:

1. purpose;
2. prerequisites;
3. environment variables;
4. install/sync command;
5. run command;
6. test/check command, if available;
7. notes for common troubleshooting.
