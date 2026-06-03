from pathlib import Path
import os

from dotenv import load_dotenv
from langsmith import traceable

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=False)

if os.environ.get("LANGSMITH_TRACING"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", os.environ["LANGSMITH_TRACING"])
    
if os.environ.get("LANGCHAIN_PROJECT"):
    os.environ.setdefault("LANGCHAIN_PROJECT", os.environ["LANGCHAIN_PROJECT"])
    
if os.environ.get("LANGSMITH_API_KEY"):
    os.environ.setdefault("LANGCHAIN_API_KEY", os.environ["LANGSMITH_API_KEY"])
    
os.environ.setdefault("LANGCHAIN_CALLBACKS_BACKGROUND", "false")

@traceable(name="langsmith_env_check", run_type="chain")
def check_langsmith() -> dict[str, str]:
    return {"status" : "ok"}

def main() -> None:
    print("LANGSMITH_TRACING =", os.environ.get("LANGSMITH_TRACING"))
    print("LANGCHAIN_PROJECT =", os.environ.get("LANGCHAIN_PROJECT"))
    print("LANGSMITH_API_KEY_SET =", bool(os.environ.get("LANGSMITH_API_KEY_SET")))
    print(check_langsmith())
    

if __name__ == "__main__":
    main()