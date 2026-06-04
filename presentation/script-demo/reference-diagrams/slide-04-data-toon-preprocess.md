# Slide 04. Data Source and TOON Preprocessing

## 사용 위치

- PPT slide 4
- 발표 구간: 데이터 출처와 전처리

## 슬라이드에서 말할 내용

`law.go.kr` API에서 법령/조례 JSON을 수집하고, 조문 단위 document로 정리한 뒤, 최종 RAG 입력은 TOON으로 변환했다. TOON 변환으로 전체 토큰 합계 기준 40.81%를 절감했다.

## 원본 근거

- `rag/code_reference/collect.py`
- `rag/code_reference/collect_ordinance.py`
- `rag/code_reference/preprocess_law.py`
- `rag/code_reference/preprocess_ordinance.py`
- `rag/RAG_PREPROCESSED_DATA/README.md`
- `rag/RAG_PREPROCESSED_DATA/rag_datas`

## Mermaid

```mermaid
flowchart LR
    LawApi["law.go.kr DRF API\nlawSearch.do / lawService.do"] --> RawLawJson["Raw law JSON\n법령 본문/조문 구조"]
    OrdinApi["law.go.kr DRF API\ntarget=ordin"] --> RawOrdinJson["Raw ordinance JSON\n조례 검색 결과/본문"]

    RawLawJson --> LawPreprocess["preprocess_law.py\n조문 단위 document 추출"]
    RawOrdinJson --> OrdinPreprocess["preprocess_ordinance.py\n조례 조문/메타데이터 추출"]

    LawPreprocess --> Toon["TOON files\nrag/RAG_PREPROCESSED_DATA/rag_datas"]
    OrdinPreprocess --> Toon

    Toon --> RagUpload["RAG FE upload\n.toon supported"]
    RagUpload --> MemgraphDoc["Memgraph Document\nraw_content + metadata"]

    TokenStats["Token efficiency\n320,991 -> 189,997\n40.81% saved"] -.-> Toon
```

## PPT 구성 제안

- 왼쪽 60%: 위 Mermaid를 단순화한 pipeline.
- 오른쪽 40%: token compression 숫자 카드.
- 하단 작은 문구: `절감률은 문서별 평균이 아니라 전체 토큰 합계 기준`.

