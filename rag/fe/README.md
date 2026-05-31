# RAG Frontend

Bun + Vite + React 기반의 RAG 운영 UI입니다. 루트 `frontend/` 서비스와 독립적으로 실행됩니다.

## Stack

- React
- React Router
- TypeScript
- Tailwind CSS
- shadcn/ui

## Run

```bash
bun install
bun run dev
```

Default URL:

```text
http://127.0.0.1:5173
```

## Environment

```bash
cp .env.example .env
```

```env
VITE_RAG_API_BASE_URL="http://127.0.0.1:8010"
VITE_RAG_API_TIMEOUT_MS=1500
VITE_RAG_ENABLE_MOCK_FALLBACK=true
VITE_MEMGRAPH_LAB_URL="http://127.0.0.1:3000"
```

RAG backend이 응답하지 않으면 FE API client가 mock data를 즉시 제공합니다. `VITE_RAG_ENABLE_MOCK_FALLBACK=false`로 끌 수 있습니다.
사이드바의 Memgraph 항목은 `VITE_MEMGRAPH_LAB_URL`을 새 창으로 엽니다.
Review Queue는 문서별 connection candidate를 카드 큐로 보여주고, 각 candidate에 대해 Approve/Deny와 reviewer note를 전송합니다.

## Checks

```bash
bun run lint
bun run build
```

## Source Structure

```txt
src/
├── App.tsx            # 라우팅 조립
├── components/        # layout, workspace, shadcn/ui 컴포넌트
├── features/          # documents, jobs, review, workspace 상태/기능
├── pages/             # 라우팅 대상 페이지
├── routes/            # route table and sidebar navigation
├── api/               # RAG API client
└── types.ts           # API response/request types
```
