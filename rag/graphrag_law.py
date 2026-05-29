from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is optional for this helper.
    load_dotenv = None


RAG_DIR = Path(__file__).resolve().parent
REPO_ROOT = RAG_DIR.parent

DEFAULT_SOURCE_DIR = RAG_DIR / "data" / "preprocessed"
DEFAULT_WORKSPACE_DIR = RAG_DIR / "graphrag_workspace" / "law"

DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


def load_environment() -> None:
    if load_dotenv is None:
        return

    load_dotenv(RAG_DIR / ".env")
    load_dotenv(REPO_ROOT / ".env")


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(filter(None, (clean_text(item) for item in value)))
    if isinstance(value, dict):
        if "content" in value:
            return clean_text(value["content"])
        return "\n".join(filter(None, (clean_text(item) for item in value.values())))
    return str(value).strip()


def append_line(lines: list[str], value: Any, prefix: str = "") -> None:
    text = clean_text(value)
    if text:
        lines.append(f"{prefix}{text}" if prefix else text)


def append_nested_items(lines: list[str], items: Any, text_key: str) -> None:
    for item in as_list(items):
        if isinstance(item, dict):
            append_line(lines, item.get(text_key))
            append_nested_items(lines, item.get("호"), "호내용")
            append_nested_items(lines, item.get("목"), "목내용")
        else:
            append_line(lines, item)


def law_name_from_payload(path: Path, payload: dict[str, Any]) -> str:
    basic = payload.get("법령", {}).get("기본정보", {})
    name = clean_text(basic.get("법령명_한글"))
    if name:
        return name
    return path.stem.removesuffix("_raw").removesuffix("_전처리")


def render_article(law_name: str, unit: dict[str, Any]) -> str:
    lines: list[str] = []

    article_no = clean_text(unit.get("조문번호"))
    branch_no = clean_text(unit.get("조문가지번호"))
    title = clean_text(unit.get("조문제목"))
    article_label = f"제{article_no}조"
    if branch_no:
        article_label += f"의{branch_no}"

    if unit.get("조문여부") == "조문":
        heading = f"[{law_name} {article_label}"
        if title:
            heading += f" {title}"
        lines.append(f"{heading}]")

    append_line(lines, unit.get("조문내용"))
    append_nested_items(lines, unit.get("항"), "항내용")

    references = clean_text(unit.get("조문참고자료"))
    if references:
        lines.append("[참고자료]")
        lines.append(references)

    return "\n".join(lines).strip()


def render_appendix(law_name: str, appendix: dict[str, Any]) -> str:
    title = clean_text(appendix.get("별표제목")) or "별표"
    lines = [f"[{law_name} {title}]"]
    append_line(lines, appendix.get("별표내용"))
    return "\n".join(lines).strip()


def convert_law_json_to_text(path: Path) -> tuple[str, str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "법령" not in payload:
        raise ValueError(f"지원하지 않는 법령 JSON 구조입니다: {path}")

    law = payload["법령"]
    law_name = law_name_from_payload(path, payload)
    basic = law.get("기본정보", {})
    article_units = as_list(law.get("조문", {}).get("조문단위"))
    appendix_units = as_list(law.get("별표", {}).get("별표단위"))

    sections: list[str] = [
        "=" * 80,
        f"법령명: {law_name}",
        f"법령ID: {clean_text(basic.get('법령ID'))}",
        f"소관부처: {clean_text(basic.get('소관부처'))}",
        f"공포번호: {clean_text(basic.get('공포번호'))}",
        f"시행일자: {clean_text(basic.get('시행일자'))}",
        "=" * 80,
        "",
    ]

    count = 0
    for unit in article_units:
        if not isinstance(unit, dict):
            continue
        rendered = render_article(law_name, unit)
        if rendered:
            sections.append(rendered)
            sections.append("")
            if unit.get("조문여부") == "조문":
                count += 1

    for appendix in appendix_units:
        if not isinstance(appendix, dict):
            continue
        rendered = render_appendix(law_name, appendix)
        if rendered:
            sections.append(rendered)
            sections.append("")

    return law_name, "\n".join(sections).strip() + "\n", count


def prepare_directories(workspace_dir: Path, clean_input: bool) -> tuple[Path, Path, Path]:
    input_dir = workspace_dir / "input"
    output_dir = workspace_dir / "output"
    cache_dir = workspace_dir / "cache"

    for directory in (input_dir, output_dir, cache_dir):
        directory.mkdir(parents=True, exist_ok=True)

    if clean_input:
        for text_file in input_dir.glob("*.txt"):
            text_file.unlink()

    return input_dir, output_dir, cache_dir


def write_input_files(source_dir: Path, input_dir: Path) -> list[tuple[str, int]]:
    if not source_dir.exists():
        raise FileNotFoundError(f"법령 JSON 디렉터리를 찾을 수 없습니다: {source_dir}")

    results: list[tuple[str, int]] = []
    for path in sorted(source_dir.glob("*_raw.json")):
        law_name, content, article_count = convert_law_json_to_text(path)
        output_path = input_dir / f"{law_name}.txt"
        output_path.write_text(content, encoding="utf-8")
        results.append((law_name, article_count))

    if not results:
        raise FileNotFoundError(f"변환할 *_raw.json 파일이 없습니다: {source_dir}")

    return results


def write_settings(workspace_dir: Path, llm_model: str, embedding_model: str) -> Path:
    settings = f"""# Generated by rag/graphrag_law.py
encoding_model: cl100k_base

completion_models:
  default_completion_model:
    type: litellm
    model_provider: openai
    model: ${{GRAPHRAG_LLM_MODEL}}
    auth_method: api_key
    api_key: ${{GRAPHRAG_API_KEY}}
    call_args:
      temperature: 0
      max_tokens: 4000

embedding_models:
  default_embedding_model:
    type: litellm
    model_provider: openai
    model: ${{GRAPHRAG_EMBEDDING_MODEL}}
    auth_method: api_key
    api_key: ${{GRAPHRAG_API_KEY}}

input:
  type: text
  storage:
    type: file
    base_dir: input
  encoding: utf-8
  file_pattern: ".*\\\\.txt$"

chunking:
  type: tokens
  encoding_model: cl100k_base
  size: 1200
  overlap: 100

output:
  type: file
  base_dir: output

cache:
  type: json
  storage:
    type: file
    base_dir: cache

reporting:
  type: file
  base_dir: output/reports

vector_store:
  type: lancedb
  db_uri: output/lancedb

extract_graph:
  completion_model_id: default_completion_model
  entity_types:
    - 법령
    - 조문
    - 권리
    - 의무
    - 기관
    - 대상
    - 조건
    - 급여
    - 벌칙
  max_gleanings: 1

summarize_descriptions:
  completion_model_id: default_completion_model
  max_length: 500
  max_input_length: 8000

community_reports:
  completion_model_id: default_completion_model
  max_length: 2000
  max_input_length: 8000

cluster_graph:
  max_cluster_size: 10

embed_text:
  embedding_model_id: default_embedding_model
  names:
    - text_unit_text
    - entity_description
    - community_full_content

local_search:
  completion_model_id: default_completion_model
  embedding_model_id: default_embedding_model
  text_unit_prop: 0.5
  community_prop: 0.1
  conversation_history_max_turns: 5
  top_k_entities: 10
  top_k_relationships: 10
  max_context_tokens: 12000

global_search:
  completion_model_id: default_completion_model
  data_max_tokens: 12000
  map_max_length: 1000
  reduce_max_length: 2000
"""
    settings_path = workspace_dir / "settings.yaml"
    settings_path.write_text(settings, encoding="utf-8")

    os.environ.setdefault("GRAPHRAG_LLM_MODEL", llm_model)
    os.environ.setdefault("GRAPHRAG_EMBEDDING_MODEL", embedding_model)

    return settings_path


def find_graphrag_command() -> list[str]:
    executable = shutil.which("graphrag")
    if executable:
        return [executable]
    return [sys.executable, "-m", "graphrag"]


def require_graphrag_installed(command: list[str]) -> None:
    result = subprocess.run(
        [*command, "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "GraphRAG 실행 파일을 찾지 못했습니다. 이 환경에 graphrag를 설치한 뒤 다시 실행하세요."
        )


def graphrag_env(llm_model: str, embedding_model: str) -> dict[str, str]:
    env = os.environ.copy()
    api_key = env.get("GRAPHRAG_API_KEY") or env.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("GRAPHRAG_API_KEY 또는 OPENAI_API_KEY 환경 변수가 필요합니다.")

    env["GRAPHRAG_API_KEY"] = api_key
    env.setdefault("GRAPHRAG_LLM_MODEL", llm_model)
    env.setdefault("GRAPHRAG_EMBEDDING_MODEL", embedding_model)
    return env


def run_index(workspace_dir: Path, command: list[str], env: dict[str, str]) -> None:
    result = subprocess.run(
        [*command, "index", "--root", str(workspace_dir), "--verbose"],
        cwd=REPO_ROOT,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError("GraphRAG 인덱싱에 실패했습니다.")


def run_query(
    workspace_dir: Path,
    command: list[str],
    env: dict[str, str],
    method: str,
    question: str,
) -> None:
    result = subprocess.run(
        [*command, "query", "--root", str(workspace_dir), "--method", method, question],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "GraphRAG 질의에 실패했습니다.")

    print(result.stdout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="법령 JSON을 Microsoft GraphRAG 입력으로 변환하고 선택적으로 인덱싱/질의를 실행합니다."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE_DIR)
    parser.add_argument("--llm-model", default=os.getenv("DEFAULT_MODEL", DEFAULT_LLM_MODEL))
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--no-clean-input", action="store_true")
    parser.add_argument("--index", action="store_true", help="입력/설정 생성 후 GraphRAG 인덱싱을 실행합니다.")
    parser.add_argument("--query", action="append", default=[], help="인덱싱된 그래프에 질의합니다. 여러 번 지정할 수 있습니다.")
    parser.add_argument("--method", choices=("local", "global", "basic", "drift"), default="local")
    parser.add_argument("--test-queries", action="store_true", help="법령 테스트 질의를 local/global로 실행합니다.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_environment()

    workspace_dir = args.workspace.resolve()
    source_dir = args.source_dir.resolve()

    input_dir, _, _ = prepare_directories(workspace_dir, clean_input=not args.no_clean_input)
    converted = write_input_files(source_dir, input_dir)
    settings_path = write_settings(workspace_dir, args.llm_model, args.embedding_model)

    print(f"작업 폴더: {workspace_dir}")
    print(f"설정 파일: {settings_path}")
    print("변환된 법령:")
    for law_name, article_count in converted:
        print(f"  - {law_name}: {article_count}개 조문")

    should_run_graphrag = args.index or args.query or args.test_queries
    if not should_run_graphrag:
        print("입력 파일과 settings.yaml 생성을 완료했습니다. 인덱싱하려면 --index 옵션을 붙여 실행하세요.")
        return 0

    command = find_graphrag_command()
    require_graphrag_installed(command)
    env = graphrag_env(args.llm_model, args.embedding_model)

    if args.index:
        print("GraphRAG 인덱싱을 시작합니다. API 비용과 시간이 발생할 수 있습니다.")
        run_index(workspace_dir, command, env)
        print("GraphRAG 인덱싱을 완료했습니다.")

    for question in args.query:
        print(f"\n[{args.method}] {question}")
        run_query(workspace_dir, command, env, args.method, question)

    if args.test_queries:
        local_questions = [
            "퇴직금을 못 받았어요. 어떻게 해야 하나요?",
            "최저임금보다 적게 받고 있어요. 신고할 수 있나요?",
            "65세 이상 노인이 받을 수 있는 혜택은 뭐가 있나요?",
        ]
        global_questions = [
            "이 법령들에서 고령자를 보호하는 공통적인 내용은 뭔가요?",
            "근로자와 노인 모두에게 적용되는 법령은 어떤 것들이 있나요?",
        ]
        for question in local_questions:
            print(f"\n[local] {question}")
            run_query(workspace_dir, command, env, "local", question)
        for question in global_questions:
            print(f"\n[global] {question}")
            run_query(workspace_dir, command, env, "global", question)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        raise SystemExit(1)
