from __future__ import annotations

from settings import settings


def dependency_summary() -> dict[str, object]:
    return {
        "runtime": "Microsoft GraphRAG",
        "settings": "pydantic-settings",
        "workspace_dir": str(settings.workspace_dir),
        "input_dir": str(settings.input_dir),
        "output_dir": str(settings.output_dir),
        "cache_dir": str(settings.cache_dir),
    }


def main() -> None:
    for key, value in dependency_summary().items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
