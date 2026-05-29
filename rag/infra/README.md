# RAG Infra

RAG 로컬 개발용 인프라 실행 파일을 관리합니다.

## Memgraph

공식 Memgraph Docker Compose 및 Memgraph Lab Docker 문서 기준으로 `memgraph/memgraph-mage`와 `memgraph/lab`을 함께 실행합니다.

```bash
cp infra/.env.example infra/.env
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

서비스 포트:

- Memgraph Bolt: `127.0.0.1:${MEMGRAPH_BOLT_PORT:-7687}`
- Memgraph logs for Lab: `${MEMGRAPH_LOG_PORT:-7444}`
- Memgraph Lab: `http://127.0.0.1:${MEMGRAPH_LAB_PORT:-3000}`

Compose는 기본적으로 host publish를 `127.0.0.1`에만 바인딩합니다. 원격 서버에서 작업할 때는 client에서 아래 포트를 포워딩해서 사용합니다.

```bash
ssh -L 3000:127.0.0.1:3000 <server>
```

VS Code Remote/port forwarding을 쓰는 경우 remote port `3000`을 forward하면 됩니다. frontend 등 다른 서비스가 `3000`을 쓰면 `infra/.env`에서 `MEMGRAPH_LAB_PORT=3001`로 바꾸고 remote port `3001`을 forward하세요.

Memgraph Lab 컨테이너는 Compose network 안에서 `QUICK_CONNECT_MG_HOST=memgraph`, `QUICK_CONNECT_MG_PORT=7687`로 DB에 붙도록 설정되어 있습니다. 브라우저에서 Lab만 열면 같은 Compose stack의 Memgraph DB를 선택할 수 있습니다.

RAG 서버는 기본적으로 아래 값으로 Memgraph에 접속합니다.

```bash
RAG_MEMGRAPH_URI=bolt://127.0.0.1:7687
```

## Check

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml ps
docker exec -it rag-memgraph mgconsole
```

Memgraph Lab만 다시 받거나 업데이트하고 싶으면:

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml pull lab
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d lab
```

## Stop

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml down
```

데이터까지 모두 지우려면 named volume도 함께 삭제합니다.

```bash
docker compose --env-file infra/.env -f infra/docker-compose.yml down -v
```

참고 문서:

- Memgraph Docker Compose: https://memgraph.com/docs/getting-started/install-memgraph/docker-compose
- Memgraph Lab Docker: https://memgraph.com/docs/memgraph-lab/getting-started/installation-and-deployment#install-memgraph-lab-with-docker
