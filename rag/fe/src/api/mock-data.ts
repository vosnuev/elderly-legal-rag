import type {
  CreateDocumentIngestJobRequest,
  FileIngestStatusResponse,
  GraphTaskSnapshot,
  MemoryDocument,
  MemoryDocumentUpdateRequest,
  RagDocument,
  RelationshipCandidate,
  ReviewDecisionRequest,
  ReviewCandidateResponse,
  ReviewCandidateStatusFilter,
  ReviewJobDecisionRequest,
} from '@/types'

const nowSuffix = () => new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)
const mockBaseDate = '2026-05-31T08:30:00.000Z'

function createMockTask(
  jobId: string,
  kind: 'construction' | 'review_action',
  status: GraphTaskSnapshot['status'],
  candidateId?: string,
): GraphTaskSnapshot {
  const idempotencyKey =
    kind === 'construction'
      ? `construction:${jobId}`
      : `review:${jobId}:${candidateId ?? 'candidate'}`
  return {
    task_id: `mock-task-${idempotencyKey.replace(/[^a-zA-Z0-9]+/g, '-')}`,
    kind,
    status,
    idempotency_key: idempotencyKey,
    submitted_at: new Date().toISOString(),
    finished_at: status === 'succeeded' || status === 'failed' ? new Date().toISOString() : null,
    error: null,
  }
}

const mockDocuments: RagDocument[] = [
  {
    content:
      '장애인 고용 지원 제도는 사업주와 근로자에게 고용 장려금, 직무 적응 지원, 근로 지원인 서비스를 제공할 수 있습니다.',
    source_title: '장애인 고용 지원 제도 안내',
    file_name: 'mock-disability-employment.md',
    file_type: 'md',
    created_at: '2026-05-31T08:30:00.000Z',
    indexed_at: '2026-05-31T08:36:00.000Z',
    updated_at: '2026-05-31T08:40:00.000Z',
    document_id: 'mock-document-001',
    job_id: 'mock-job-001',
    location: 'mock://documents/disability-employment',
    url: 'https://example.local/mock/disability-employment',
  },
  {
    content:
      '근로기준법은 근로계약, 임금, 근로시간, 휴게, 휴일 등 기본적인 근로조건을 정하고 있습니다.',
    source_title: '근로기준법 주요 조항 요약',
    file_name: 'mock-labor-standards.json',
    file_type: 'json',
    created_at: '2026-05-31T08:45:00.000Z',
    indexed_at: '2026-05-31T08:51:00.000Z',
    updated_at: '2026-05-31T08:54:00.000Z',
    document_id: 'mock-document-002',
    job_id: 'mock-job-002',
    location: 'mock://documents/labor-standards',
    url: 'https://example.local/mock/labor-standards',
  },
]

const mockJobs: FileIngestStatusResponse[] = [
  {
    job_id: 'mock-job-001',
    file_name: 'mock-disability-employment.md',
    current_stage: 'pending_review',
    completed: false,
    created_at: mockBaseDate,
    updated_at: '2026-05-31T08:40:00.000Z',
    stages: [
      {
        stage: 'uploaded',
        status: 'success',
        message: 'Mock document uploaded.',
      },
      {
        stage: 'uploaded_to_database',
        status: 'success',
        message: 'Mock document stored in database.',
      },
      {
        stage: 'graph_add_started',
        status: 'success',
        message: 'Mock graph construction task finished.',
      },
      {
        stage: 'pending_review',
        status: 'success',
        message: 'Mock graph ingest produced relationship candidates.',
      },
    ],
    document_id: 'mock-document-001',
    chunk_count: 2,
    candidate_count: 21,
    pending_review_count: 21,
    current_task: createMockTask('mock-job-001', 'construction', 'succeeded'),
    warning: 'Mock data is being used because the RAG backend is unavailable.',
  },
]

let mockMemory: MemoryDocument = {
  exists: true,
  id: 'mock-memory-global',
  scope: 'global',
  title: 'Candidate extraction memory',
  content:
    '## 후보 생성 기준\n\n- 사용자가 반려한 관계 유형은 다음 후보 생성에서 보수적으로 적용한다.\n- reviewer note가 있는 경우 해당 note를 우선 기준으로 삼는다.',
  version: 1,
  status: 'active',
  author: 'mock',
  updated_at: mockBaseDate,
  metadata: {
    format: 'curated_markdown',
  },
  evidence_review_note_ids: [],
  evidence_candidate_ids: [],
}

const mockReviewCandidates: RelationshipCandidate[] = [
  {
    id: 'mock-candidate-001',
    job_id: 'mock-job-001',
    source_node: '장애인 고용 지원 제도',
    target_node: '근로 지원인 서비스',
    relationship_type: 'REFERENCES',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text:
      '장애인 고용 지원 제도는 사업주와 근로자에게 고용 장려금, 직무 적응 지원, 근로 지원인 서비스를 제공할 수 있습니다.',
    rationale: '지원 제도 설명에서 근로 지원인 서비스가 직접 근거로 언급됩니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text:
        '장애인 고용 지원 제도는 사업주와 근로자에게 고용 장려금, 직무 적응 지원, 근로 지원인 서비스를 제공할 수 있습니다.',
      target_chunk_id: 'mock-chunk-disability-002',
      target_chunk_label: 'Chunk #2',
      target_chunk_text:
        '근로 지원인 서비스는 중증장애인 근로자가 안정적으로 직무를 수행할 수 있도록 보조 인력을 지원하는 제도입니다.',
      confidence: 0.86,
    },
  },
  {
    id: 'mock-candidate-003',
    job_id: 'mock-job-001',
    source_node: '사업주',
    target_node: '고용 장려금',
    relationship_type: 'RECEIVES',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text:
      '장애인 고용 지원 제도는 사업주와 근로자에게 고용 장려금, 직무 적응 지원, 근로 지원인 서비스를 제공할 수 있습니다.',
    rationale: '지원 제도에서 사업주에게 고용 장려금을 제공한다는 점이 텍스트에 직관적으로 명시되어 있습니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text:
        '장애인 고용 지원 제도는 사업주와 근로자에게 고용 장려금, 직무 적응 지원, 근로 지원인 서비스를 제공할 수 있습니다.',
      target_chunk_id: 'mock-chunk-disability-003',
      target_chunk_label: 'Chunk #3',
      target_chunk_text:
        '고용 장려금은 장애인을 신규 채용하거나 고용을 유지하는 사업주에게 지급되는 재정적 인센티브입니다.',
      confidence: 0.92,
    },
  },
  {
    id: 'mock-candidate-004',
    job_id: 'mock-job-001',
    source_node: '근로자',
    target_node: '직무 적응 지원',
    relationship_type: 'BENEFITS_FROM',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text:
      '장애인 고용 지원 제도는 사업주와 근로자에게 고용 장려금, 직무 적응 지원, 근로 지원인 서비스를 제공할 수 있습니다.',
    rationale: '장애인 근로자가 직장에 잘 적응하도록 직무 적응 지원 프로그램이 혜택으로 주어집니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text:
        '장애인 고용 지원 제도는 사업주와 근로자에게 고용 장려금, 직무 적응 지원, 근로 지원인 서비스를 제공할 수 있습니다.',
      target_chunk_id: 'mock-chunk-disability-004',
      target_chunk_label: 'Chunk #4',
      target_chunk_text:
        '직무 적응 지원은 장애인 근로자가 새로운 업무 환경과 동료 관계에 연착륙하도록 전문가 상담 및 교육을 제공합니다.',
      confidence: 0.81,
    },
  },
  {
    id: 'mock-candidate-005',
    job_id: 'mock-job-001',
    source_node: '중증장애인 근로자',
    target_node: '보조 인력',
    relationship_type: 'ASSISTED_BY',
    source_chunk_id: 'mock-chunk-disability-002',
    evidence_text:
      '근로 지원인 서비스는 중증장애인 근로자가 안정적으로 직무를 수행할 수 있도록 보조 인력을 지원하는 제도입니다.',
    rationale: '중증장애인 근로자가 안정적으로 직무를 완수할 수 있게 보조 인력을 매칭하는 역학이 서술되어 있습니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #2',
      source_chunk_text:
        '근로 지원인 서비스는 중증장애인 근로자가 안정적으로 직무를 수행할 수 있도록 보조 인력을 지원하는 제도입니다.',
      target_chunk_id: 'mock-chunk-disability-005',
      target_chunk_label: 'Chunk #5',
      target_chunk_text:
        '보조 인력(근로 지원인)은 수어 통역, 시각 보조, 서류 대필 등의 세부 전문 조력을 제공합니다.',
      confidence: 0.95,
    },
  },
  {
    id: 'mock-candidate-006',
    job_id: 'mock-job-001',
    source_node: '장애인 고용 장려금',
    target_node: '채용 인센티브',
    relationship_type: 'REFERENCES',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '장애인 고용 장려금은 신규 고용에 따른 경제적 부담을 완화해주는 대표적인 채용 인센티브입니다.',
    rationale: '고용 장려금이 실질적인 채용 인센티브로 작동하고 있음을 설명합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '장애인 고용 장려금은 신규 고용에 따른 경제적 부담을 완화해주는 대표적인 채용 인센티브입니다.',
      target_chunk_id: 'mock-chunk-disability-006',
      target_chunk_label: 'Chunk #6',
      target_chunk_text: '채용 인센티브는 기업의 장애인 고용 장벽을 완화하고 일자리 기회를 확장합니다.',
      confidence: 0.88,
    },
  },
  {
    id: 'mock-candidate-007',
    job_id: 'mock-job-001',
    source_node: '보조공학기기 지원',
    target_node: '직무 능률',
    relationship_type: 'INCREASES',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '보조공학기기 지원을 통해 장애인 근로자의 물리적 제약을 극복하고 직무 능률을 극대화할 수 있습니다.',
    rationale: '보조공학기기가 제공됨으로써 직무 능률이 직접적으로 향상된다는 인과관계가 있습니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '보조공학기기 지원을 통해 장애인 근로자의 물리적 제약을 극복하고 직무 능률을 극대화할 수 있습니다.',
      target_chunk_id: 'mock-chunk-disability-007',
      target_chunk_label: 'Chunk #7',
      target_chunk_text: '직무 능률 향상은 장애인 근로자의 고용 안정을 돕고 만족도를 대폭 향상시킵니다.',
      confidence: 0.91,
    },
  },
  {
    id: 'mock-candidate-008',
    job_id: 'mock-job-001',
    source_node: '장애인 의무 고용률',
    target_node: '상시 근로자수',
    relationship_type: 'DETERMINED_BY',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '장애인 의무 고용률은 해당 기업의 상시 근로자수에 따라 동적으로 산출되고 결정됩니다.',
    rationale: '의무 고용 기준이 상시 근로자수 규모에 의존적으로 정해짐을 텍스트가 설명합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '장애인 의무 고용률은 해당 기업의 상시 근로자수에 따라 동적으로 산출되고 결정됩니다.',
      target_chunk_id: 'mock-chunk-disability-008',
      target_chunk_label: 'Chunk #8',
      target_chunk_text: '상시 근로자수 50인 이상 민간기업은 전체 정원의 3.1% 이상 장애인을 고용할 법적 의무가 있습니다.',
      confidence: 0.85,
    },
  },
  {
    id: 'mock-candidate-009',
    job_id: 'mock-job-001',
    source_node: '장애인 근로자',
    target_node: '표준 사업장',
    relationship_type: 'WORKS_AT',
    source_chunk_id: 'mock-chunk-disability-002',
    evidence_text: '장애인 표준 사업장은 10명 이상의 장애인 근로자를 안정적으로 고용하고 있는 우수 작업 환경 모델입니다.',
    rationale: '장애인 근로자가 고용되어 상시 근로하고 있는 대상지로서 표준 사업장이 소개됩니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #2',
      source_chunk_text: '장애인 표준 사업장은 10명 이상의 장애인 근로자를 안정적으로 고용하고 있는 우수 작업 환경 모델입니다.',
      target_chunk_id: 'mock-chunk-disability-009',
      target_chunk_label: 'Chunk #9',
      target_chunk_text: '표준 사업장은 장애인 편의시설을 완비하고 친화적 근로 분위기를 보장하는 인증 기관입니다.',
      confidence: 0.89,
    },
  },
  {
    id: 'mock-candidate-010',
    job_id: 'mock-job-001',
    source_node: '고용노동부',
    target_node: '고용 장려금',
    relationship_type: 'ADMINISTERS',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '고용노동부는 장애인 의무 고용 비율을 초과한 기업들을 장려하기 위해 고용 장려금 제도를 관리/운영합니다.',
    rationale: '장려금 제도를 책임지고 운영하는 관리 주체로서 고용노동부를 식별합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '고용노동부는 장애인 의무 고용 비율을 초과한 기업들을 장려하기 위해 고용 장려금 제도를 관리/운영합니다.',
      target_chunk_id: 'mock-chunk-disability-010',
      target_chunk_label: 'Chunk #10',
      target_chunk_text: '고용 장려금 행정 청구 및 심사 과정은 공단 지사를 통해 고용노동부에 최종 보고 및 집행됩니다.',
      confidence: 0.94,
    },
  },
  {
    id: 'mock-candidate-011',
    job_id: 'mock-job-001',
    source_node: '직업 능력 개발원',
    target_node: '맞춤형 훈련',
    relationship_type: 'PROVIDES',
    source_chunk_id: 'mock-chunk-disability-002',
    evidence_text: '장애인 직업 능력 개발원은 개별 적성을 반영한 산업체 맞춤형 훈련 과정을 전국 교육생에게 무상 지원합니다.',
    rationale: '능력개발원이 훈련 프로그램을 공급하는 주체임을 서술합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #2',
      source_chunk_text: '장애인 직업 능력 개발원은 개별 적성을 반영한 산업체 맞춤형 훈련 과정을 전국 교육생에게 무상 지원합니다.',
      target_chunk_id: 'mock-chunk-disability-011',
      target_chunk_label: 'Chunk #11',
      target_chunk_text: '맞춤형 훈련 과정은 IT, 기계, 행정 등 유망 직군을 집중 타겟하여 즉각적인 실무 투입을 돕습니다.',
      confidence: 0.83,
    },
  },
  {
    id: 'mock-candidate-012',
    job_id: 'mock-job-001',
    source_node: '한국장애인고용공단',
    target_node: '구인구직 상담',
    relationship_type: 'OPERATES',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '한국장애인고용공단은 취업 취약 계층의 자립을 위해 전담 구인구직 상담 창구를 전국적으로 연중 가동합니다.',
    rationale: '구인구직 연계 상담 인프라를 운영하는 공공 기관이 공단임을 맵핑합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '한국장애인고용공단은 취업 취약 계층의 자립을 위해 전담 구인구직 상담 창구를 전국적으로 연중 가동합니다.',
      target_chunk_id: 'mock-chunk-disability-012',
      target_chunk_label: 'Chunk #12',
      target_chunk_text: '상담 창구에서는 심층 상담과 직무 매칭, 동행 면접 등의 맞춤 취업 솔루션을 1:1로 밀착 관리합니다.',
      confidence: 0.87,
    },
  },
  {
    id: 'mock-candidate-013',
    job_id: 'mock-job-001',
    source_node: '상시 근로자 50명 이상',
    target_node: '장애인 의무고용',
    relationship_type: 'APPLIES_TO',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '법적 장애인 의무고용 조항은 상시 근로자 50명 이상을 고용한 모든 민간 사업장에 보편적으로 적용됩니다.',
    rationale: '의무고용 적용 기준 요건이 상시 근로자 50명 규모임을 연관 지어 줍니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '법적 장애인 의무고용 조항은 상시 근로자 50명 이상을 고용한 모든 민간 사업장에 보편적으로 적용됩니다.',
      target_chunk_id: 'mock-chunk-disability-013',
      target_chunk_label: 'Chunk #13',
      target_chunk_text: '의무 고용률을 위반한 기업에게는 매년 고용노동부가 산정한 미이행 부담금이 차등 부과됩니다.',
      confidence: 0.90,
    },
  },
  {
    id: 'mock-candidate-014',
    job_id: 'mock-job-001',
    source_node: '국가 및 지방자치단체',
    target_node: '의무 고용 비율',
    relationship_type: 'COMPLIES_WITH',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '국가 및 지방자치단체는 일반 민간기업보다 엄격한 3.6%의 장애인 의무 고용 비율 조항을 철저히 준수해야 합니다.',
    rationale: '공공 영역의 의무 이행 비율에 대한 법규 관계를 렌더링합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '국가 및 지방자치단체는 일반 민간기업보다 엄격한 3.6%의 장애인 의무 고용 비율 조항을 철저히 준수해야 합니다.',
      target_chunk_id: 'mock-chunk-disability-014',
      target_chunk_label: 'Chunk #14',
      target_chunk_text: '공공부문 장애인 고용 실태는 매년 고용노동부 장관을 통해 언론에 공식적으로 투명하게 공표됩니다.',
      confidence: 0.93,
    },
  },
  {
    id: 'mock-candidate-015',
    job_id: 'mock-job-001',
    source_node: '고용 장려금 지급 기준',
    target_node: '고용률 초과 달성',
    relationship_type: 'CONDITIONED_UPON',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '고용 장려금 지급 기준의 핵심은 의무적으로 할당된 법정 고용률을 초과 달성하여 적극 고용하는 것입니다.',
    rationale: '장려금 신청 조건이 의무율 초과 고용임을 짚어줍니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '고용 장려금 지급 기준의 핵심은 의무적으로 할당된 법정 고용률을 초과 달성하여 적극 고용하는 것입니다.',
      target_chunk_id: 'mock-chunk-disability-015',
      target_chunk_label: 'Chunk #15',
      target_chunk_text: '초과 채용된 장애인 1인당 월 최소 35만원에서 최대 90만원 범위 내로 성별 및 장애정도별 차등 지원합니다.',
      confidence: 0.84,
    },
  },
  {
    id: 'mock-candidate-016',
    job_id: 'mock-job-001',
    source_node: '장애인 표준 사업장',
    target_node: '세제 혜택',
    relationship_type: 'RECEIVES',
    source_chunk_id: 'mock-chunk-disability-002',
    evidence_text: '정식 인증된 장애인 표준 사업장은 신규 설립 시 법인세/소득세 감면 등 다양한 세제 혜택을 국세청으로부터 부여받습니다.',
    rationale: '표준 사업장의 경제적 혜택으로서의 세무 인센티브를 정리합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #2',
      source_chunk_text: '정식 인증된 장애인 표준 사업장은 신규 설립 시 법인세/소득세 감면 등 다양한 세제 혜택을 국세청으로부터 부여받습니다.',
      target_chunk_id: 'mock-chunk-disability-016',
      target_chunk_label: 'Chunk #16',
      target_chunk_text: '세제 혜택에는 최초 소득 발생 과세연도부터 3년간 세액의 100%, 이후 2년간 50% 감면 특례 조항이 포함됩니다.',
      confidence: 0.96,
    },
  },
  {
    id: 'mock-candidate-017',
    job_id: 'mock-job-001',
    source_node: '직무 지도원',
    target_node: '적응 훈련 프로그램',
    relationship_type: 'FACILITATES',
    source_chunk_id: 'mock-chunk-disability-002',
    evidence_text: '현장 배치된 직무 지도원은 발달장애인 근로자가 직장에서 소외되지 않도록 맞춤 적응 훈련 프로그램을 주도합니다.',
    rationale: '적응 프로그램의 진행 촉진자로서 직무 지도원을 설정합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #2',
      source_chunk_text: '현장 배치된 직무 지도원은 발달장애인 근로자가 직장에서 소외되지 않도록 맞춤 적응 훈련 프로그램을 주도합니다.',
      target_chunk_id: 'mock-chunk-disability-017',
      target_chunk_label: 'Chunk #17',
      target_chunk_text: '적응 훈련 프로그램은 일상 매너, 직무 절차 학습, 갈등 대처 방법 등을 포함하는 통합 사회화 세션입니다.',
      confidence: 0.82,
    },
  },
  {
    id: 'mock-candidate-018',
    job_id: 'mock-job-001',
    source_node: '보조공학기기',
    target_node: '휠체어 리프트',
    relationship_type: 'INCLUDES',
    source_chunk_id: 'mock-chunk-disability-002',
    evidence_text: '무상 대여되는 작업환경 개선 보조공학기기 범위에는 특수 제작된 전동 휠체어 리프트 장치 등도 광범위하게 포함됩니다.',
    rationale: '장비 분류에 휠체어 리프트가 직접적인 실례로 포함됨을 묘사합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #2',
      source_chunk_text: '무상 대여되는 작업환경 개선 보조공학기기 범위에는 특수 제작된 전동 휠체어 리프트 장치 등도 광범위하게 포함됩니다.',
      target_chunk_id: 'mock-chunk-disability-018',
      target_chunk_label: 'Chunk #18',
      target_chunk_text: '리프트 장치 및 점자 단말기 등 연간 1인당 최대 1,500만원(중증 2,000만원) 한도로 구매 및 무상 지원이 이뤄집니다.',
      confidence: 0.89,
    },
  },
  {
    id: 'mock-candidate-019',
    job_id: 'mock-job-001',
    source_node: '장애인 인식개선 교육',
    target_node: '모든 사업주',
    relationship_type: 'MANDATED_FOR',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '장애인 고용촉진법상 직장 내 인식개선 교육은 모든 사업주 및 근로자가 매년 1회 이상 이수해야 하는 의무조항입니다.',
    rationale: '인식개선 교육이 전 임직원 및 사업주에게 법적 의무 사항임을 연결합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '장애인 고용촉진법상 직장 내 인식개선 교육은 모든 사업주 및 근로자가 매년 1회 이상 이수해야 하는 의무조항입니다.',
      target_chunk_id: 'mock-chunk-disability-019',
      target_chunk_label: 'Chunk #19',
      target_chunk_text: '교육 미실시 기업에는 적발 시 상시 300만원 이하의 과태료가 예외 없이 강제 부과될 수 있습니다.',
      confidence: 0.92,
    },
  },
  {
    id: 'mock-candidate-020',
    job_id: 'mock-job-001',
    source_node: '장애인 의무고용 미이행',
    target_node: '고용부담금',
    relationship_type: 'INCURS',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '장애인 의무고용 미이행 시 고용부담금이 가차없이 부과되며, 이는 채용 인건비보다 과중한 재정적 위험으로 돌아옵니다.',
    rationale: '고용 의무 불이행 시의 법적 부담금 부과 인과 관계를 서술합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '장애인 의무고용 미이행 시 고용부담금이 가차없이 부과되며, 이는 채용 인건비보다 과중한 재정적 위험으로 돌아옵니다.',
      target_chunk_id: 'mock-chunk-disability-020',
      target_chunk_label: 'Chunk #20',
      target_chunk_text: '부담금 납부 대상은 상시 근로자 100인 이상을 고용한 민간기업 및 공공기관으로 규정됩니다.',
      confidence: 0.88,
    },
  },
  {
    id: 'mock-candidate-021',
    job_id: 'mock-job-001',
    source_node: '중증장애인 2배수 인정',
    target_node: '고용률 산정',
    relationship_type: 'MULTIPLIED_BY',
    source_chunk_id: 'mock-chunk-disability-001',
    evidence_text: '중증장애인 근로자를 채용한 경우, 2배수 인정 제도를 적용하여 법정 고용률 산정 시 가산 혜택을 부여합니다.',
    rationale: '중증장애인 고용 활성화를 위한 고용률 가산 산정 규칙을 설명합니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-001',
      document_title: '장애인 고용 지원 제도 안내',
      file_name: 'mock-disability-employment.md',
      source_chunk_label: 'Chunk #1',
      source_chunk_text: '중증장애인 근로자를 채용한 경우, 2배수 인정 제도를 적용하여 법정 고용률 산정 시 가산 혜택을 부여합니다.',
      target_chunk_id: 'mock-chunk-disability-021',
      target_chunk_label: 'Chunk #21',
      target_chunk_text: '가산 산정은 월 소정근로시간 60시간 이상 근무 시에 한하여 유효하게 가산 적용됩니다.',
      confidence: 0.95,
    },
  },
  {
    id: 'mock-candidate-002',
    job_id: 'mock-job-002',
    source_node: '근로기준법 주요 조항',
    target_node: '근로시간',
    relationship_type: 'RELATED_TO',
    source_chunk_id: 'mock-chunk-labor-001',
    evidence_text:
      '근로기준법은 근로계약, 임금, 근로시간, 휴게, 휴일 등 기본적인 근로조건을 정하고 있습니다.',
    rationale: '문서의 핵심 조항 요약에 근로시간이 근로조건의 한 축으로 포함됩니다.',
    status: 'pending_review',
    version: 1,
    metadata: {
      document_id: 'mock-document-002',
      document_title: '근로기준법 주요 조항 요약',
      file_name: 'mock-labor-standards.json',
      source_chunk_label: 'Chunk #1',
      source_chunk_text:
        '근로기준법은 근로계약, 임금, 근로시간, 휴게, 휴일 등 기본적인 근로조건을 정하고 있습니다.',
      target_chunk_id: 'mock-chunk-labor-002',
      target_chunk_label: 'Chunk #2',
      target_chunk_text:
        '근로시간 조항은 법정 근로시간, 연장근로 제한, 휴게시간 산정과 직접 연결됩니다.',
      confidence: 0.78,
    },
  },
]

export function getMockDocuments(): RagDocument[] {
  return [...mockDocuments]
}

export function getMockJobs(): FileIngestStatusResponse[] {
  return [...mockJobs]
}

export function createMockIngestJob(
  payload: CreateDocumentIngestJobRequest,
): FileIngestStatusResponse {
  const suffix = nowSuffix()
  const jobId = `mock-job-${suffix}`
  const documentId = `mock-document-${suffix}`
  const fileType = payload.file_name.split('.').pop() || 'txt'
  const now = new Date().toISOString()

  const job: FileIngestStatusResponse = {
    job_id: jobId,
    file_name: payload.file_name,
    current_stage: 'graph_add_started',
    completed: false,
    created_at: now,
    updated_at: now,
    stages: [
      {
        stage: 'uploaded',
        status: 'success',
        message: 'Mock document uploaded.',
      },
      {
        stage: 'uploaded_to_database',
        status: 'success',
        message: 'Mock document stored in database.',
      },
      {
        stage: 'graph_add_started',
        status: 'pending',
        message: 'Mock graph construction task was queued.',
      },
    ],
    document_id: documentId,
    chunk_count: Math.max(1, Math.ceil(payload.content.length / 800)),
    candidate_count: 0,
    pending_review_count: 0,
    current_task: createMockTask(jobId, 'construction', 'queued'),
    warning: 'Mock data is being used because the RAG backend is unavailable.',
  }

  mockJobs.unshift(job)
  mockDocuments.unshift({
    content: payload.content,
    source_title: payload.file_name,
    file_name: payload.file_name,
    file_type: fileType,
    created_at: job.created_at,
    indexed_at: job.updated_at,
    updated_at: job.updated_at,
    document_id: documentId,
    job_id: jobId,
    location: `mock://documents/${documentId}`,
  })

  return job
}

export function startMockGraphAdd(jobId: string): FileIngestStatusResponse {
  const existingJob = mockJobs.find((job) => job.job_id === jobId)
  const job = existingJob ?? {
    job_id: jobId,
    file_name: `${jobId}.txt`,
    current_stage: 'uploaded_to_database',
    completed: false,
    stages: [],
    chunk_count: 0,
    candidate_count: 0,
    pending_review_count: 0,
  }

  ensureMockCandidatesForJob(job)
  const pendingForJob = mockReviewCandidates.filter(
    (candidate) => candidate.job_id === job.job_id && candidate.status === 'pending_review',
  )
  const constructionTask: GraphTaskSnapshot =
    job.current_task?.kind === 'construction'
      ? { ...job.current_task, status: 'succeeded', finished_at: new Date().toISOString() }
      : createMockTask(job.job_id, 'construction', 'succeeded')

  const startedJob: FileIngestStatusResponse = {
    ...job,
    current_stage: 'pending_review',
    completed: false,
    stages: [
      ...job.stages,
      {
        stage: 'graph_add_started',
        status: 'success',
        message: 'Mock graph add started.',
      },
      {
        stage: 'pending_review',
        status: 'success',
        message: 'Mock graph ingest produced relationship candidates.',
      },
    ],
    candidate_count: Math.max(job.candidate_count ?? 0, pendingForJob.length),
    pending_review_count: pendingForJob.length,
    current_task: constructionTask,
    warning: 'Mock data is being used because the RAG backend is unavailable.',
  }

  const existingIndex = mockJobs.findIndex((item) => item.job_id === jobId)
  if (existingIndex >= 0) {
    mockJobs.splice(existingIndex, 1, startedJob)
  } else {
    mockJobs.unshift(startedJob)
  }

  return startedJob
}

export function getMockReviewCandidates(
  status: ReviewCandidateStatusFilter = 'pending',
): ReviewCandidateResponse {
  const candidates = mockReviewCandidates.filter((candidate) => {
    if (status === 'all') {
      return true
    }
    if (status === 'finished') {
      return candidate.status !== 'pending_review'
    }
    return candidate.status === 'pending_review'
  })

  return {
    columns: ['candidate'],
    rows: candidates.map((candidate) => ({
      candidate: {
        type: 'node',
        element_id: candidate.id,
        labels: ['RelationshipCandidate'],
        properties: candidate,
      },
    })),
    row_count: candidates.length,
    elapsed_ms: 0,
  }
}

export function getMockMemory(): MemoryDocument {
  return { ...mockMemory }
}

export function updateMockMemory(payload: MemoryDocumentUpdateRequest): MemoryDocument {
  mockMemory = {
    ...mockMemory,
    exists: true,
    title: payload.title?.trim() || mockMemory.title,
    content: payload.content.trim(),
    version: mockMemory.version + 1,
    status: 'active',
    author: payload.author ?? 'rag-fe',
    updated_at: new Date().toISOString(),
    metadata: {
      format: 'curated_markdown',
      last_update_summary: payload.update_summary ?? '',
    },
  }
  return getMockMemory()
}

export function submitMockReviewDecision(
  candidateId: string,
  payload: ReviewDecisionRequest,
): FileIngestStatusResponse {
  return submitMockReviewJobDecisions('mock-review', {
    decisions: [
      {
        candidate_id: candidateId,
        action: payload.action,
        note: payload.note,
      },
    ],
    reviewer: payload.reviewer,
  })
}

export function submitMockReviewJobDecisions(
  jobId: string,
  payload: ReviewJobDecisionRequest,
): FileIngestStatusResponse {
  let lastCandidate: RelationshipCandidate | null = null
  for (const decision of payload.decisions) {
    const candidateIndex = mockReviewCandidates.findIndex(
      (candidate) => candidate.id === decision.candidate_id,
    )
    if (candidateIndex < 0) {
      continue
    }
    const candidate = mockReviewCandidates[candidateIndex]
    if (jobId !== 'mock-review' && candidate.job_id !== jobId) {
      continue
    }
    lastCandidate = candidate
    mockReviewCandidates.splice(candidateIndex, 1, {
      ...candidate,
      review_action: decision.action,
      review_note: decision.note ?? null,
      reviewed_at: new Date().toISOString(),
      reviewer: payload.reviewer ?? 'rag-fe',
      status: decision.action === 'yes' ? 'approved' : 'rejected',
      metadata: {
        ...candidate.metadata,
        reviewer: payload.reviewer ?? 'rag-fe',
        reviewer_note: decision.note ?? '',
      },
    })
  }

  const effectiveJobId = lastCandidate?.job_id ?? jobId
  const jobCandidates = mockReviewCandidates.filter((item) => item.job_id === effectiveJobId)
  const pendingReviewCount = jobCandidates.filter((item) => item.status === 'pending_review').length
  const existingJob = mockJobs.find((job) => job.job_id === effectiveJobId)
  const stage = pendingReviewCount > 0 ? 'pending_review' : 'completed'

  if (!lastCandidate) {
    return {
      job_id: effectiveJobId,
      file_name: existingJob?.file_name ?? 'mock-review.txt',
      current_stage: stage,
      completed: stage === 'completed',
      stages: existingJob?.stages ?? [],
      document_id: existingJob?.document_id,
      chunk_count: existingJob?.chunk_count ?? 0,
      candidate_count: jobCandidates.length,
      pending_review_count: pendingReviewCount,
      warning: 'Mock candidate was already reviewed.',
    }
  }

  const reviewedJob: FileIngestStatusResponse = {
    job_id: effectiveJobId,
    file_name:
      existingJob?.file_name ??
      getStringMetadata(lastCandidate, 'file_name') ??
      `${effectiveJobId}.txt`,
    current_stage: stage,
    completed: stage === 'completed',
    stages: [
      ...(existingJob?.stages ?? []),
      {
        stage,
        status: 'success',
        message: 'Mock review decision batch task finished.',
      },
    ],
    document_id: getStringMetadata(lastCandidate, 'document_id') ?? existingJob?.document_id,
    chunk_count: existingJob?.chunk_count ?? 0,
    candidate_count: jobCandidates.length,
    pending_review_count: pendingReviewCount,
    current_task: createMockTask(effectiveJobId, 'review_action', 'succeeded', 'batch'),
    warning: 'Mock data is being used because the RAG backend is unavailable.',
  }

  const existingJobIndex = mockJobs.findIndex((job) => job.job_id === effectiveJobId)
  if (existingJobIndex >= 0) {
    mockJobs.splice(existingJobIndex, 1, reviewedJob)
  } else {
    mockJobs.unshift(reviewedJob)
  }

  return reviewedJob
}

function ensureMockCandidatesForJob(job: FileIngestStatusResponse) {
  const alreadyExists = mockReviewCandidates.some((candidate) => candidate.job_id === job.job_id)
  if (alreadyExists) {
    return
  }

  const documentTitle = job.file_name.replace(/\.[^.]+$/, '')
  mockReviewCandidates.unshift(
    {
      id: `${job.job_id}-candidate-001`,
      job_id: job.job_id,
      source_node: documentTitle,
      target_node: '기존 그래프 엔티티',
      relationship_type: 'RELATED_TO',
      source_chunk_id: `${job.document_id ?? job.job_id}-chunk-001`,
      evidence_text: 'Mock graph add가 새 문서에서 추출한 관계 후보입니다.',
      rationale: '새 문서의 핵심 문장과 기존 그래프 엔티티가 의미적으로 연결됩니다.',
      status: 'pending_review',
      version: 1,
      metadata: {
        document_id: job.document_id,
        document_title: documentTitle,
        file_name: job.file_name,
        source_chunk_label: 'Generated chunk #1',
        source_chunk_text: 'Mock graph add가 새 문서에서 추출한 관계 후보입니다.',
        target_chunk_id: `${job.document_id ?? job.job_id}-related-chunk-001`,
        target_chunk_label: 'Related graph chunk',
        target_chunk_text: '기존 그래프에서 의미적으로 가까운 chunk context입니다.',
        confidence: 0.72,
      },
    },
    {
      id: `${job.job_id}-candidate-002`,
      job_id: job.job_id,
      source_node: documentTitle,
      target_node: '검토 대상 정책',
      relationship_type: 'MENTIONS',
      source_chunk_id: `${job.document_id ?? job.job_id}-chunk-002`,
      evidence_text: 'Mock graph add가 같은 문서의 다른 문단에서 추출한 관계 후보입니다.',
      rationale: '문서 내 표현이 정책 주제와 연결될 가능성이 있어 검토가 필요합니다.',
      status: 'pending_review',
      version: 1,
      metadata: {
        document_id: job.document_id,
        document_title: documentTitle,
        file_name: job.file_name,
        source_chunk_label: 'Generated chunk #2',
        source_chunk_text: 'Mock graph add가 같은 문서의 다른 문단에서 추출한 관계 후보입니다.',
        target_chunk_id: `${job.document_id ?? job.job_id}-related-chunk-002`,
        target_chunk_label: 'Review target chunk',
        target_chunk_text: '검토 대상 정책과 연결될 수 있는 기존 graph chunk context입니다.',
        confidence: 0.69,
      },
    },
  )
}

// function countPendingCandidates() {
//   return mockReviewCandidates.filter((candidate) => candidate.status === 'pending_review').length
// }

function getStringMetadata(candidate: RelationshipCandidate, key: string) {
  const value = candidate.metadata[key]
  return typeof value === 'string' ? value : null
}
