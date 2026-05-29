from functools import lru_cache
from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent


# prompt markdown 파일을 읽어 문자열로 반환
@lru_cache
def load_prompt(file_name: str) -> str:
    prompt_path = PROMPT_DIR / file_name
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")
