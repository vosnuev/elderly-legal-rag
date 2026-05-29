---
name: uv-python
description: Use this skill for Python setup, dependency management, and run commands in backend/, rag/, and streamlit/.
---

# uv Python Skill

Python projects in this repository must use `uv`.

## Rules

- Use `uv init`, `uv add`, `uv sync`, `uv lock`, and `uv run`.
- Do not use `pip`, `pip3`, Poetry, or root-level `requirements.txt` for project dependency management.
- Keep each Python service self-contained with its own `pyproject.toml`, `uv.lock`, and `.python-version`.
- Do not commit `.venv/`.

## Backend

Run commands from inside `backend/`:

```bash
uv sync
uv run fastapi dev src/app.py
```

Add backend dependencies from inside `backend/`:

```bash
uv add <package>
```

## RAG

Run commands from inside `rag/`:

```bash
uv sync
uv run python src/app.py
```

Add RAG dependencies from inside `rag/`:

```bash
uv add <package>
```

## Streamlit

Run commands from inside `streamlit/`:

```bash
uv sync
uv run streamlit run src/app.py
```

Add Streamlit dependencies from inside `streamlit/`:

```bash
uv add <package>
```

## Lock Files

Commit `uv.lock` when dependency metadata changes.
