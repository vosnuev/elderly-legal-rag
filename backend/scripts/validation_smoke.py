from pathlib import Path
import os

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env", override=False)

if os.environ.get("LANGSMITH_TRACING"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", os.environ["LANGSMITH_TRACING"])
    
if os.environ.get("LANGSMITH_PROJECT"):
    os.environ.setdefault("LANGCHAIN_PROJECT", os.environ["LANGSMITH_PROJECT"])
    
if os.environ.get("LANGSMITH_API_KEY"):
    os.environ.setdefault("LANGCHAIN_API_KEY", os.environ["LANGSMITH_API_KEY"])
    
os.environ.setdefault("LANGCHAIN_CALLBACKS_BACKGROUND", "false")

from agent.graph import run_agent
from parse_testcases import TESTCASE_FILE, parse_markdown_table

def main() -> None:
    testcases = parse_markdown_table(TESTCASE_FILE)
    testcase = testcases[0]
    
    print(f"testcase_id : {testcase['testcase_id']}")
    print(f"query: {testcase['query']}")
    print(f"model: {os.environ.get('BACKEND_OPENROUTER_MODEL')}")
    print(f"provider_order: {os.environ.get('BACKEND_OPENROUTER_PROVIDER_ORDER')}")
    print(f"allow_fallbacks: {os.environ.get('BACKEND_OPENROUTER_ALLOW_FALLBACKS')}")
    print()
    
    for tool_mode, use_tools in [
        ("no_tool", False),                  # ("with_tool", True) 나중에 넣기 아래에   
    ]:
        print("=" * 80)
        print(f"tool_mode : {tool_mode}")
        print("=" * 80)
        
        answer = run_agent(
            testcase["query"],
            session_id=f"smoke-{testcase['testcase_id']}-{tool_mode}",
            use_tools=use_tools,
        )
        
        print(answer[:1000])
        print()

if __name__ == "__main__":
    main()
