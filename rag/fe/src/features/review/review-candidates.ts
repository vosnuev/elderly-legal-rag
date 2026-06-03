import type {
  RelationshipCandidate,
  ReviewCandidateResponse,
} from '@/types'

type UnknownRecord = Record<string, unknown>

export type ReviewCandidateGroup = {
  candidates: RelationshipCandidate[]
  documentKey: string
  documentLabel: string
}

export type ReviewCandidateJobGroup = {
  candidates: RelationshipCandidate[]
  documentLabel: string
  fileName: string | null
  jobId: string
}

export function normalizeReviewCandidates(
  response: ReviewCandidateResponse | null,
): RelationshipCandidate[] {
  return (response?.rows ?? [])
    .map(readCandidateRecord)
    .map((record, index) => normalizeCandidate(record, index))
    .filter((candidate): candidate is RelationshipCandidate => candidate !== null)
}

export function groupReviewCandidatesByDocument(
  candidates: RelationshipCandidate[],
): ReviewCandidateGroup[] {
  const groups = new Map<string, ReviewCandidateGroup>()

  for (const candidate of candidates) {
    const documentKey = getCandidateDocumentKey(candidate)
    const documentLabel = getCandidateDocumentLabel(candidate)
    const group = groups.get(documentKey)

    if (group) {
      group.candidates.push(candidate)
    } else {
      groups.set(documentKey, {
        candidates: [candidate],
        documentKey,
        documentLabel,
      })
    }
  }

  return Array.from(groups.values())
}

export function groupReviewCandidatesByJob(
  candidates: RelationshipCandidate[],
): ReviewCandidateJobGroup[] {
  const groups = new Map<string, ReviewCandidateJobGroup>()

  for (const candidate of candidates) {
    const jobId = candidate.job_id
    const group = groups.get(jobId)

    if (group) {
      group.candidates.push(candidate)
    } else {
      groups.set(jobId, {
        candidates: [candidate],
        documentLabel: getCandidateDocumentLabel(candidate),
        fileName: getMetadataString(candidate, ['file_name']),
        jobId,
      })
    }
  }

  return Array.from(groups.values())
}

export function getCandidateDocumentLabel(candidate: RelationshipCandidate) {
  return (
    getMetadataString(candidate, ['document_title', 'source_title', 'file_name', 'title']) ??
    candidate.job_id
  )
}

function readCandidateRecord(row: unknown): UnknownRecord | null {
  if (Array.isArray(row)) {
    return readCandidateRecord(row[0])
  }

  const rowRecord = asRecord(row)
  if (!rowRecord) {
    return null
  }

  const candidateValue =
    rowRecord.candidate ??
    rowRecord.relationship_candidate ??
    rowRecord.rc ??
    rowRecord.properties ??
    rowRecord
  const candidateRecord = asRecord(candidateValue)
  if (!candidateRecord) {
    return null
  }

  return asRecord(candidateRecord.properties) ?? candidateRecord
}

function normalizeCandidate(
  record: UnknownRecord | null,
  index: number,
): RelationshipCandidate | null {
  if (!record) {
    return null
  }

  const metadata = normalizeMetadata(record.metadata)
  copyMetadataField(record, metadata, 'document_id')
  copyMetadataField(record, metadata, 'document_title')
  copyMetadataField(record, metadata, 'source_title')
  copyMetadataField(record, metadata, 'file_name')
  copyMetadataField(record, metadata, 'source_chunk_text')
  copyMetadataField(record, metadata, 'source_chunk_name')
  copyMetadataField(record, metadata, 'source_chunk_description')
  copyMetadataField(record, metadata, 'source_chunk_summary')
  copyMetadataField(record, metadata, 'source_chunk_index')
  copyMetadataField(record, metadata, 'source_chunk_label')
  copyMetadataField(record, metadata, 'target_chunk_id')
  copyMetadataField(record, metadata, 'target_chunk_text')
  copyMetadataField(record, metadata, 'target_chunk_name')
  copyMetadataField(record, metadata, 'target_chunk_description')
  copyMetadataField(record, metadata, 'target_chunk_summary')
  copyMetadataField(record, metadata, 'target_chunk_index')
  copyMetadataField(record, metadata, 'target_chunk_label')
  copyMetadataField(record, metadata, 'evidence_chunk_name')
  copyMetadataField(record, metadata, 'evidence_chunk_description')
  copyMetadataField(record, metadata, 'evidence_chunk_summary')
  copyMetadataField(record, metadata, 'evidence_chunk_index')
  copyMetadataField(record, metadata, 'target_document_title')
  copyMetadataField(record, metadata, 'confidence')
  copyMetadataField(record, metadata, 'review_action')
  copyMetadataField(record, metadata, 'review_note')
  copyMetadataField(record, metadata, 'reviewed_at')
  copyMetadataField(record, metadata, 'reviewer')

  const sourceNode = readString(record, ['source_node', 'source', 'from'], 'Unknown source')
  const targetNode = readString(record, ['target_node', 'target', 'to'], 'Unknown target')

  return {
    id: readString(record, ['id', 'candidate_id'], `candidate-${index + 1}`),
    job_id: readString(record, ['job_id'], 'unknown-job'),
    source_node: sourceNode,
    target_node: targetNode,
    relationship_type: readString(
      record,
      ['relationship_type', 'relationship', 'type'],
      'RELATED_TO',
    ).toUpperCase(),
    source_chunk_id: readString(record, ['source_chunk_id', 'chunk_id'], ''),
    source_chunk_name: readOptionalString(record, ['source_chunk_name']),
    source_chunk_description: readOptionalString(record, ['source_chunk_description']),
    source_chunk_summary: readOptionalString(record, ['source_chunk_summary']),
    source_chunk_text: readOptionalString(record, ['source_chunk_text']),
    source_chunk_label: readOptionalString(record, ['source_chunk_label']),
    target_chunk_id: readOptionalString(record, ['target_chunk_id']),
    target_chunk_name: readOptionalString(record, ['target_chunk_name']),
    target_chunk_description: readOptionalString(record, ['target_chunk_description']),
    target_chunk_summary: readOptionalString(record, ['target_chunk_summary']),
    target_chunk_text: readOptionalString(record, ['target_chunk_text']),
    target_chunk_label: readOptionalString(record, ['target_chunk_label']),
    evidence_chunk_name: readOptionalString(record, ['evidence_chunk_name']),
    evidence_chunk_description: readOptionalString(record, ['evidence_chunk_description']),
    evidence_text: readString(record, ['evidence_text', 'evidence', 'source_text'], ''),
    rationale: readString(record, ['rationale', 'reason'], ''),
    review_action: readOptionalString(record, ['review_action']),
    review_note: readOptionalString(record, ['review_note']),
    reviewed_at: readOptionalString(record, ['reviewed_at']),
    reviewer: readOptionalString(record, ['reviewer', 'reviewed_by']),
    status: readString(record, ['status'], 'pending_review'),
    version: readNumber(record.version, 1),
    metadata,
  }
}

function getCandidateDocumentKey(candidate: RelationshipCandidate) {
  return (
    getMetadataString(candidate, ['document_id', 'file_name', 'document_title', 'source_title']) ??
    candidate.job_id
  )
}

function getMetadataString(candidate: RelationshipCandidate, keys: string[]) {
  for (const key of keys) {
    const value = candidate.metadata[key]
    if (typeof value === 'string' && value.trim()) {
      return value
    }
  }

  return null
}

function copyMetadataField(
  record: UnknownRecord,
  metadata: Record<string, unknown>,
  key: string,
) {
  if (metadata[key] === undefined && record[key] !== undefined) {
    metadata[key] = record[key]
  }
}

function normalizeMetadata(value: unknown): Record<string, unknown> {
  const metadata = asRecord(value)
  if (metadata) {
    return { ...metadata }
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value) as unknown
      const parsedRecord = asRecord(parsed)
      return parsedRecord ? { ...parsedRecord } : {}
    } catch {
      return {}
    }
  }

  return {}
}

function readString(record: UnknownRecord, keys: string[], fallback: string) {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) {
      return value
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value)
    }
  }

  return fallback
}

function readOptionalString(record: UnknownRecord, keys: string[]) {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) {
      return value
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value)
    }
  }
  return null
}

function readNumber(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asRecord(value: unknown): UnknownRecord | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null
}
