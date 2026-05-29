from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path


def _load_real_streamlit_package() -> None:
    current_dir = Path(__file__).resolve().parent
    search_paths = [
        path
        for path in sys.path
        if Path(path or ".").resolve() != current_dir
    ]
    spec = importlib.machinery.PathFinder.find_spec("streamlit", search_paths)
    if spec is None or spec.loader is None:
        raise ImportError("Could not find installed streamlit package")

    module = importlib.util.module_from_spec(spec)
    sys.modules[__name__] = module
    spec.loader.exec_module(module)


def _run_app() -> None:
    src_dir = Path(__file__).resolve().parent / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from app import main

    main()


if __name__ == "__main__":
    _run_app()
else:
    _load_real_streamlit_package()
