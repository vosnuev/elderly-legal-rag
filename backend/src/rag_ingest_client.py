from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from schemas.files import FileIngestStatusResponse, RagIngestRequest


# RAG ingest 서버 호출 실패
class RagIngestClientError(RuntimeError):
    pass

# backend가 저장한 파일 정보 -> RAG ingest 서버에 전달
def request_rag_ingest(payload: RagIngestRequest) -> None:
    from settings import settings

    request = Request(
        settings.rag_ingest_url,
        data=payload.model_dump_json().encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=settings.rag_ingest_timeout_ms / 1000) as response:
            response.read()
    except HTTPError as exc:
        raise RagIngestClientError(f"RAG ingest 서버가 HTTP {exc.code} 응답을 반환했습니다.") from exc
    except TimeoutError as exc:
        raise RagIngestClientError("RAG ingest 요청 시간이 초과되었습니다.") from exc
    except URLError as exc:
        raise RagIngestClientError(f"RAG ingest 서버에 연결할 수 없습니다.: {exc.reason}") from exc


# RAG ingest 서버에서 job 처리 상태 조회
def get_rag_ingest_status(job_id: str) -> FileIngestStatusResponse:
    from settings import settings

    url = f"{settings.rag_ingest_status_url.rstrip('/')}/{job_id}"
    request = Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=settings.rag_ingest_timeout_ms / 1000) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        raise RagIngestClientError(f"RAG ingest 상태 조회가 HTTP {exc.code} 응답을 반환했습니다.") from exc
    except TimeoutError as exc:
        raise RagIngestClientError("RAG ingest 상태 조회 시간이 초과되었습니다.") from exc
    except URLError as exc:
        raise RagIngestClientError(f"RAG ingest 서버에 연결할 수 없습니다.: {exc.reason}") from exc

    return FileIngestStatusResponse.model_validate_json(body)
