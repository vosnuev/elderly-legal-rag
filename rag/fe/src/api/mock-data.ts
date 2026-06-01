import type {
  CreateDocumentIngestJobRequest,
  FileIngestStatusResponse,
  GraphTaskSnapshot,
  RagDocument,
  RelationshipCandidate,
  ReviewDecisionRequest,
  ReviewCandidateResponse,
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
    candidate_count: 5,
    pending_review_count: 5,
    current_task: createMockTask('mock-job-001', 'construction', 'succeeded'),
    warning: 'Mock data is being used because the RAG backend is unavailable.',
  },
]

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

export function getMockReviewCandidates(): ReviewCandidateResponse {
  const pendingCandidates = mockReviewCandidates.filter(
    (candidate) => candidate.status === 'pending_review',
  )

  return {
    columns: ['candidate'],
    rows: pendingCandidates.map((candidate) => ({
      candidate: {
        type: 'node',
        element_id: candidate.id,
        labels: ['RelationshipCandidate'],
        properties: candidate,
      },
    })),
    row_count: pendingCandidates.length,
    elapsed_ms: 0,
  }
}

export function submitMockReviewDecision(
  candidateId: string,
  payload: ReviewDecisionRequest,
): FileIngestStatusResponse {
  const candidateIndex = mockReviewCandidates.findIndex((candidate) => candidate.id === candidateId)
  const actionStatus = {
    no: 'rejected',
    retry: 'needs_retry',
    yes: 'approved',
  } satisfies Record<ReviewDecisionRequest['action'], string>

  if (candidateIndex < 0) {
    return {
      job_id: 'mock-review',
      file_name: 'mock-review.txt',
      current_stage: 'completed',
      completed: true,
      stages: [],
      chunk_count: 0,
      candidate_count: mockReviewCandidates.length,
      pending_review_count: countPendingCandidates(),
      warning: 'Mock candidate was already reviewed.',
    }
  }

  const candidate = mockReviewCandidates[candidateIndex]
  const reviewedCandidate: RelationshipCandidate = {
    ...candidate,
    status: actionStatus[payload.action],
    metadata: {
      ...candidate.metadata,
      reviewer: payload.reviewer ?? 'rag-fe',
      reviewer_note: payload.note ?? '',
    },
  }
  mockReviewCandidates.splice(candidateIndex, 1, reviewedCandidate)

  const jobCandidates = mockReviewCandidates.filter((item) => item.job_id === candidate.job_id)
  const pendingReviewCount = jobCandidates.filter((item) => item.status === 'pending_review').length
  const existingJob = mockJobs.find((job) => job.job_id === candidate.job_id)
  const stage = pendingReviewCount > 0 ? 'pending_review' : 'completed'
  const reviewedJob: FileIngestStatusResponse = {
    job_id: candidate.job_id,
    file_name:
      existingJob?.file_name ??
      getStringMetadata(candidate, 'file_name') ??
      `${candidate.job_id}.txt`,
    current_stage: stage,
    completed: stage === 'completed',
    stages: [
      ...(existingJob?.stages ?? []),
      {
        stage,
        status: 'success',
        message: 'Mock review decision task finished.',
      },
    ],
    document_id: getStringMetadata(candidate, 'document_id') ?? existingJob?.document_id,
    chunk_count: existingJob?.chunk_count ?? 0,
    candidate_count: jobCandidates.length,
    pending_review_count: pendingReviewCount,
    current_task: createMockTask(candidate.job_id, 'review_action', 'succeeded', candidateId),
    warning: 'Mock data is being used because the RAG backend is unavailable.',
  }

  const existingJobIndex = mockJobs.findIndex((job) => job.job_id === candidate.job_id)
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

function countPendingCandidates() {
  return mockReviewCandidates.filter((candidate) => candidate.status === 'pending_review').length
}

function getStringMetadata(candidate: RelationshipCandidate, key: string) {
  const value = candidate.metadata[key]
  return typeof value === 'string' ? value : null
}
