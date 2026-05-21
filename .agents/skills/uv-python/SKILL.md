---
name: uv-python
description: Use this skill for Python setup, dependency management, and run commands in backend/ and streamlit/.
---

# uv Python Skill

Python projects in this repository must use `uv`.

## Rules

- Use `uv init`, `uv add`, `uv sync`, `uv lock`, and `uv run`.
- Do not use `pip`, `pip3`, Poetry, or root-level `requirements.txt` for project dependency management.
- Keep each Python service self-contained with its own `pyproject.toml`, `uv.lock`, and `.python-version`.
- Do not commit `.venv/`.

## Backend

```bash
cd backend
uv sync
uv run python main.py
```

Add backend dependencies from inside `backend/`:

```bash
uv add <package>
```

## Streamlit

```bash
cd streamlit
uv sync
uv run streamlit run main.py
```

Add Streamlit project dependencies from inside `streamlit/`:

```bash
uv add <package>
```

## Lock Files

Commit `uv.lock` when dependency metadata changes.
