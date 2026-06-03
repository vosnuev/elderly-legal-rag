from pathlib import Path

TESTCASE_FILE = Path("data/testcases/rag_agent_question_test_cases.md")

def parse_markdown_table(path : Path) -> list[dict[str, str]]:
    rows = []
    
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        
        if not line.startswith("| RAG-Q-"):
            continue
        
        columns = [column.strip() for column in line.strip("|").split("|")]
        
        rows.append(
            {
                "testcase_id" : columns[0],
                "query" :columns[1],
                "expected_keywords" : columns[2],
                "reference" : columns[3],
                "judge_criteria" : columns[4],
                "batch" : columns[5],
                "difficulty" : columns[6],
                "special_case" : columns[7],
            }
        )
        
    return rows
    
def main() -> None:
    testcases = parse_markdown_table(TESTCASE_FILE)
    
    print(f"total testcases: {len(testcases)}")
    print()
    
    for testcase in testcases[:3]:
        print(testcase["testcase_id"])
        print(testcase["query"])
        print()
        
if __name__ == "__main__":
    main()