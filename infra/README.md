# Infra

루트 통합 Docker Compose 실행 파일을 관리합니다.

## Services

`infra/docker-compose.yml`은 아래 서비스를 같은 Docker network인
`infra_default`에 올립니다.

- `backend`: Main Agent FastAPI
- `streamlit`: 상담형 Streamlit UI
- `rag-be`: RAG Backend + FastMCP Streamable HTTP endpoint
- `rag-fe`: RAG 운영 UI
- `memgraph`: GraphRAG DB
- `lab`: Memgraph Lab
- `redis`: RAG job observability stream

`docs_web`과 `rag-red-team`은 이 통합 stack에 포함하지 않습니다.

## Env Files

실제 환경 변수 파일은 `infra/` 아래에 복사해서 Compose가 주입합니다.
이 파일들은 `.gitignore` 대상입니다.

```bash
cp infra/.env.example infra/.env
cp backend/.env infra/.env_backend
cp streamlit/.env infra/.env_streamlit
cp rag/be/.env infra/.env_rag_be
cp rag/fe/.env infra/.env_rag_fe
cp rag/infra/.env infra/.env_rag_infra
```

`infra/.env`는 host publish port 같은 non-secret Compose 변수용입니다.
서비스별 secret/API key는 `infra/.env_backend`, `infra/.env_rag_be`처럼
서비스별 파일에 둡니다.

## Run

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d --build
```

기본 host 포트:

| service | URL |
| --- | --- |
| Backend | `http://127.0.0.1:8100` |
| Streamlit | `http://127.0.0.1:8501` |
| RAG Backend | `http://127.0.0.1:8110` |
| RAG Frontend | `http://127.0.0.1:5174` |
| Memgraph Lab | `http://127.0.0.1:3000` |
| Memgraph Bolt | `bolt://127.0.0.1:7687` |
| Redis | `redis://127.0.0.1:6379/0` |

Docker network 내부 연결:

```text
backend -> http://rag-be:8010/mcp
streamlit -> http://backend:8000
rag-be -> bolt://memgraph:7687
rag-be -> redis://redis:6379/0
```

## Check

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
curl -s http://127.0.0.1:8100/health
curl -s http://127.0.0.1:8110/health
curl -s http://127.0.0.1:8501/_stcore/health
curl -s http://127.0.0.1:5174/ | head
```

Docker network 내부에서 MCP tool 목록을 확인합니다.

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml exec -T backend python - <<'PY'
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def main():
    client = MultiServerMCPClient({
        "rag": {"transport": "http", "url": "http://rag-be:8010/mcp"}
    })
    tools = await client.get_tools(server_name="rag")
    print([tool.name for tool in tools])

asyncio.run(main())
PY
```

`/chat`은 실제 LLM 호출이므로 `infra/.env_backend`의 OpenRouter API key가
유효해야 합니다. API key가 없거나 만료되면 backend는 MCP tools를 로드한 뒤
OpenRouter에서 401을 반환합니다.

## Stop

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml down
```

Memgraph/Redis 데이터 volume까지 지우려면:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml down -v
```
