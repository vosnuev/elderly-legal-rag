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
  copyMetadataField(record, metadata, 'source_chunk_label')
  copyMetadataField(record, metadata, 'target_chunk_id')
  copyMetadataField(record, metadata, 'target_chunk_text')
  copyMetadataField(record, metadata, 'target_chunk_label')
  copyMetadataField(record, metadata, 'target_document_title')
  copyMetadataField(record, metadata, 'confidence')

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
    evidence_text: readString(record, ['evidence_text', 'evidence', 'source_text'], ''),
    rationale: readString(record, ['rationale', 'reason'], ''),
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

function readNumber(value: unknown, fallback: number) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asRecord(value: unknown): UnknownRecord | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null
}
