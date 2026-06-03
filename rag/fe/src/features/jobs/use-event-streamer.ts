import { useCallback, useEffect, useRef, useState } from 'react'

import { API_BASE_URL } from '@/api/retrieve'

export type StreamLogType = 'lifecycle' | 'message' | 'error' | 'agent' | 'service'
export type StreamStatus = 'idle' | 'connecting' | 'live' | 'error'

export type ToolUsageSnapshot = {
  name: string
  arguments: Record<string, unknown>
  result?: string
}

export interface StreamEventLog {
  aggregateKey?: string
  id: string
  sourceEventId?: string
  timestamp: string
  type: StreamLogType
  text: string
  agentName?: string
  eventName?: string
  serviceName?: string
  streamChannel?: string
  subroutineKey?: string
  thought?: string
  toolUsage?: ToolUsageSnapshot
}

export type TopologyNodeId =
  | 'document_constructed'
  | 'task_queue'
  | 'chunking_agent'
  | 'embedding_dispatch'
  | 'graph_candidate_agent'
  | 'edge_materializer'
  | 'completed'

export type TopologyEdgeId =
  | 'queue_to_worker'
  | 'doc_to_queue'
  | 'queue_to_chunk'
  | 'chunk_to_embed'
  | 'embed_to_candidate'
  | 'build_result_to_job_state'
  | 'review_result_to_job_state'
  | 'materializer_to_completed'

type ObservabilityEvent = {
  event_id?: string
  job_id?: string
  channel?: string
  kind?: string | null
  payload?: Record<string, unknown>
}

type WorkerMetricSnapshot = {
  activeTasks: number
  queueCount: number
  lane?: string
}

type AddLogMeta = Omit<StreamEventLog, 'id' | 'timestamp' | 'type' | 'text'> & {
  aggregateMode?: 'append' | 'replace'
}

const MAX_JOB_LOGS = 240
const GENERIC_AGENT_LOGS = new Set([
  'messages: agent event',
  'values: agent event',
  'tools: tool',
  'tools: tool tool-started',
  'tools: tool tool-finished',
])

export function useEventStreamer(selectedJobId: string | null) {
  const [jobLogs, setJobLogs] = useState<Record<string, StreamEventLog[]>>({})
  const [jobMetrics, setJobMetrics] = useState<Record<string, WorkerMetricSnapshot>>({})
  const [liveNodes, setLiveNodes] = useState<Record<string, TopologyNodeId | null>>({})
  const [liveEdges, setLiveEdges] = useState<Record<string, TopologyEdgeId | null>>({})
  const [connectionStatus, setConnectionStatus] = useState<Record<string, StreamStatus>>({})
  const eventSourceRef = useRef<EventSource | null>(null)
  const seenEventIdsRef = useRef<Record<string, Set<string>>>({})
  const toolNameByCallIdRef = useRef<Record<string, Record<string, string>>>({})

  const addLog = useCallback((
    jobId: string,
    type: StreamLogType,
    text: string,
    meta?: AddLogMeta,
  ) => {
    const { aggregateMode, ...logMeta } = meta ?? {}
    const eventId = meta?.eventName
      ? `${meta.eventName}:${meta.streamChannel ?? ''}:${text}`
      : text
    const newLog: StreamEventLog = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      timestamp: new Date().toLocaleTimeString('ko-KR', { hour12: false }),
      type,
      text: meta?.aggregateKey && meta?.thought
        ? `model output: ${summarizeInlineText(meta.thought)}`
        : text,
      ...logMeta,
    }
    setJobLogs((prev) => {
      const currentLogs = prev[jobId] ?? []
      if (newLog.aggregateKey) {
        const aggregateIndex = currentLogs.findIndex(
          (log) => log.aggregateKey === newLog.aggregateKey,
        )
        if (aggregateIndex >= 0) {
          const existingLog = currentLogs[aggregateIndex]
          const nextThought = mergeThoughtText({
            current: existingLog.thought,
            incoming: newLog.thought,
            mode: aggregateMode ?? 'replace',
          })
          const updatedLog: StreamEventLog = {
            ...existingLog,
            eventName: newLog.eventName,
            sourceEventId: newLog.sourceEventId,
            text: nextThought
              ? `model output: ${summarizeInlineText(nextThought)}`
              : newLog.text,
            thought: nextThought,
          }
          return {
            ...prev,
            [jobId]: [
              ...currentLogs.slice(0, aggregateIndex),
              updatedLog,
              ...currentLogs.slice(aggregateIndex + 1),
            ],
          }
        }
      }

      const alreadyExists = meta?.sourceEventId
        ? currentLogs.some((log) => log.sourceEventId === meta.sourceEventId)
        : currentLogs.some(
            (log) =>
              log.eventName &&
              log.streamChannel &&
              `${log.eventName}:${log.streamChannel}:${log.text}` === eventId,
          )
      if (alreadyExists) {
        return prev
      }

      return {
        ...prev,
        [jobId]: [...currentLogs, newLog].slice(-MAX_JOB_LOGS),
      }
    })
  }, [])

  const handleObservabilityEvent = useCallback((event: ObservabilityEvent) => {
    const jobId = asString(event.job_id) ?? selectedJobId
    const payload = event.payload ?? {}

    if (!jobId) {
      return
    }

    const sourceEventId = asString(event.event_id)
    if (sourceEventId) {
      const seenEventIds = seenEventIdsRef.current[jobId] ?? new Set<string>()
      seenEventIdsRef.current[jobId] = seenEventIds
      if (seenEventIds.has(sourceEventId)) {
        return
      }
      seenEventIds.add(sourceEventId)
    }

    if (event.channel === 'worker_metrics') {
      setJobMetrics((prev) => ({
        ...prev,
        [jobId]: {
          activeTasks: asNumber(payload.active_tasks) ?? 0,
          lane: asString(payload.lane) ?? undefined,
          queueCount: asNumber(payload.queue_count) ?? 0,
        },
      }))
      return
    }

    const node = resolveTopologyNode(payload.stage, payload.agentName)
    const edge = resolveTopologyEdge(payload.edge)
    if (node) {
      setLiveNodes((prev) => ({ ...prev, [jobId]: node }))
    }
    if (edge) {
      setLiveEdges((prev) => ({ ...prev, [jobId]: edge }))
    }

    const type = normalizeLogType(payload.type, event.channel)
    const streamChannel = asString(payload.streamChannel) ?? asString(event.channel)
    const nestedPayload = asRecord(payload.payload)
    const eventName = readNestedEventName(nestedPayload) ?? asString(payload.event)
    const agentName = type === 'agent' ? asString(payload.agentName) ?? undefined : undefined
    const subroutineKey = subroutineKeyFromPayload(payload)
    const toolUsage = type === 'agent'
      ? normalizeToolUsage(payload.toolUsage, nestedPayload)
      : undefined
    const resolvedToolUsage = toolUsage
      ? resolveToolName(jobId, toolUsage, toolNameByCallIdRef.current)
      : undefined
    const thought = type === 'agent' && streamChannel === 'messages'
      ? asString(payload.thought) ??
        asString(payload.diagnosticNote) ??
        asString(payload.token) ??
        visibleTextFromNestedPayload(nestedPayload) ??
        undefined
      : undefined
    const outputAggregate = modelOutputAggregate({
      agentName,
      eventName,
      nestedPayload,
      streamChannel,
      subroutineKey,
      thought,
      toolUsage: resolvedToolUsage,
    })
    const text = outputAggregate
      ? `model output: ${thought ?? ''}`.trim()
      : formatObservabilityLog(event, resolvedToolUsage)

    if (shouldSkipObservabilityLog({ eventName, streamChannel, text, thought, toolUsage: resolvedToolUsage })) {
      return
    }

    addLog(jobId, type, text, {
      agentName,
      eventName: eventName ?? undefined,
      serviceName: type === 'service' ? asString(payload.serviceName) ?? undefined : undefined,
      streamChannel: streamChannel ?? undefined,
      subroutineKey,
      aggregateKey: outputAggregate?.key,
      aggregateMode: outputAggregate?.mode,
      sourceEventId: sourceEventId ?? undefined,
      thought,
      toolUsage: resolvedToolUsage,
    })
  }, [addLog, selectedJobId])

  useEffect(() => {
    eventSourceRef.current?.close()
    eventSourceRef.current = null

    if (!selectedJobId) {
      return undefined
    }

    const url = new URL(`/api/ingest/jobs/${encodeURIComponent(selectedJobId)}/events`, API_BASE_URL)
    const source = new EventSource(url.toString())
    eventSourceRef.current = source

    source.onopen = () => {
      setConnectionStatus((prev) => ({ ...prev, [selectedJobId]: 'live' }))
      addLog(selectedJobId, 'lifecycle', 'Connected to live job event stream.', {
        eventName: 'stream.connected',
        streamChannel: 'sse',
      })
    }

    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) {
        setConnectionStatus((prev) => ({ ...prev, [selectedJobId]: 'error' }))
        addLog(selectedJobId, 'error', 'Event stream connection closed.', {
          eventName: 'stream.closed',
          streamChannel: 'sse',
        })
        return
      }

      setConnectionStatus((prev) => ({ ...prev, [selectedJobId]: 'connecting' }))
    }

    const handleEvent = (event: MessageEvent<string>) => {
      const data = typeof event.data === 'string' ? event.data.trim() : ''
      if (!data || !data.startsWith('{')) {
        return
      }
      try {
        handleObservabilityEvent(JSON.parse(data) as ObservabilityEvent)
      } catch {
        addLog(selectedJobId, 'error', 'Received unreadable event stream payload.', {
          eventName: 'stream.parse_error',
          streamChannel: 'sse',
        })
      }
    }

    for (const eventName of ['agent_transcript', 'worker_metrics', 'lifecycle', 'service']) {
      source.addEventListener(eventName, handleEvent)
    }

    return () => {
      source.close()
      if (eventSourceRef.current === source) {
        eventSourceRef.current = null
      }
    }
  }, [addLog, handleObservabilityEvent, selectedJobId])

  const metrics = selectedJobId ? jobMetrics[selectedJobId] : undefined

  return {
    activeEdge: selectedJobId ? liveEdges[selectedJobId] ?? null : null,
    activeNode: selectedJobId ? liveNodes[selectedJobId] ?? null : null,
    activeTasks: metrics?.activeTasks ?? 0,
    logs: selectedJobId ? jobLogs[selectedJobId] ?? [] : [],
    queueCount: metrics?.queueCount ?? 0,
    streamStatus: selectedJobId ? connectionStatus[selectedJobId] ?? 'connecting' : 'idle',
    workerLane: metrics?.lane ?? null,
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function asString(value: unknown) {
  return typeof value === 'string' && value.length > 0 ? value : null
}

function asNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function normalizeLogType(type: unknown, channel: unknown): StreamLogType {
  if (
    type === 'lifecycle' ||
    type === 'message' ||
    type === 'error' ||
    type === 'agent' ||
    type === 'service'
  ) {
    return type
  }
  if (channel === 'service') {
    return 'service'
  }
  if (channel === 'error') {
    return 'error'
  }
  if (channel === 'agent_transcript') {
    return 'agent'
  }

  return 'message'
}

function mergeThoughtText({
  current,
  incoming,
  mode,
}: {
  current?: string
  incoming?: string
  mode: 'append' | 'replace'
}) {
  if (!incoming) {
    return current
  }
  if (mode === 'replace') {
    if (current && incoming.endsWith('...') && current.length > incoming.length) {
      return current
    }
    return incoming
  }
  return `${current ?? ''}${incoming}`
}

function summarizeInlineText(value: string, maxChars = 180) {
  const normalized = value.replace(/\s+/g, ' ').trim()
  if (normalized.length <= maxChars) {
    return normalized
  }
  return `${normalized.slice(0, maxChars)}...`
}

function modelOutputAggregate({
  agentName,
  eventName,
  nestedPayload,
  streamChannel,
  subroutineKey,
  thought,
  toolUsage,
}: {
  agentName?: string
  eventName: string | null
  nestedPayload: Record<string, unknown> | null
  streamChannel: string | null
  subroutineKey?: string
  thought?: string
  toolUsage?: ToolUsageSnapshot
}) {
  if (
    streamChannel !== 'messages' ||
    !thought ||
    toolUsage ||
    (eventName !== 'content-block-delta' && eventName !== 'content-block-finish')
  ) {
    return null
  }

  const metadata = asRecord(nestedPayload?.metadata)
  const runId =
    asString(metadata?.run_id) ??
    asString(nestedPayload?.id) ??
    'model-output'
  return {
    key: `${agentName ?? 'agent'}:${subroutineKey ?? 'global'}:${runId}`,
    mode: eventName === 'content-block-finish' ? 'replace' as const : 'append' as const,
  }
}

function formatObservabilityLog(
  event: ObservabilityEvent,
  toolUsage?: ToolUsageSnapshot,
) {
  const payload = event.payload ?? {}
  const token = asString(payload.token)
  if (token) {
    return `model token: ${token}`
  }

  const streamChannel = asString(payload.streamChannel)
  const nestedPayload = asRecord(payload.payload)
  const eventName = readNestedEventName(nestedPayload)

  if (toolUsage) {
    return formatToolUsageLine(streamChannel ?? 'tools', toolUsage)
  }

  const log = asString(payload.log)
  if (log && !GENERIC_AGENT_LOGS.has(log)) {
    return log
  }

  const valuesSummary = streamChannel === 'values'
    ? summarizeValuesPayload(nestedPayload)
    : null
  if (valuesSummary) {
    return `values: ${valuesSummary}`
  }

  const messageSummary = streamChannel === 'messages'
    ? summarizeMessagePayload(nestedPayload)
    : null
  if (messageSummary) {
    return `messages: ${messageSummary}`
  }

  if (streamChannel && eventName) {
    return `${streamChannel}: ${eventName}`
  }

  return `${event.channel ?? 'event'}: ${event.kind ?? 'runtime'}`
}

function normalizeToolUsage(
  value: unknown,
  nestedPayload: Record<string, unknown> | null,
): ToolUsageSnapshot | undefined {
  const usage = asRecord(value) ?? asRecord(nestedPayload?.data) ?? asRecord(nestedPayload?.tool_call)
  if (!usage) {
    return undefined
  }

  const name =
    asString(usage.name) ??
    asString(usage.tool_name) ??
    asString(usage.toolName) ??
    'tool'
  const input = asRecord(usage.arguments) ?? asRecord(usage.input) ?? usage
  const output = usage.result ?? usage.output ?? usage.error

  return {
    name,
    arguments: input,
    result: output === undefined ? undefined : JSON.stringify(output),
  }
}

function resolveToolName(
  jobId: string,
  usage: ToolUsageSnapshot,
  toolNameByCallId: Record<string, Record<string, string>>,
) {
  const toolCallId = toolCallIdFromUsage(usage)
  if (!toolCallId) {
    return usage
  }

  const jobToolNames = toolNameByCallId[jobId] ?? {}
  toolNameByCallId[jobId] = jobToolNames
  if (usage.name && usage.name !== 'tool') {
    jobToolNames[toolCallId] = usage.name
    return usage
  }

  const rememberedName = jobToolNames[toolCallId]
  return rememberedName ? { ...usage, name: rememberedName } : usage
}

function toolCallIdFromUsage(usage: ToolUsageSnapshot) {
  return (
    asString(usage.arguments.tool_call_id) ??
    asString(usage.arguments.toolCallId) ??
    asString(asRecord(usage.arguments.tool_call)?.id) ??
    null
  )
}

function formatToolUsageLine(streamChannel: string, usage: ToolUsageSnapshot) {
  const event = asString(usage.arguments.event)
  if (event) {
    return `${streamChannel}: ${usage.name} ${event}`
  }
  return `${streamChannel}: ${usage.name}`
}

function shouldSkipObservabilityLog({
  eventName,
  streamChannel,
  text,
  thought,
  toolUsage,
}: {
  eventName: string | null
  streamChannel: string | null
  text: string
  thought?: string
  toolUsage?: ToolUsageSnapshot
}) {
  if (toolUsage || thought) {
    return false
  }
  return (
    streamChannel === 'messages' &&
    eventName === 'content-block-start' &&
    text === 'messages: content-block-start'
  )
}

function readNestedEventName(payload: Record<string, unknown> | null) {
  if (!payload) {
    return null
  }
  const data = asRecord(payload.data)
  return asString(payload.event) ?? asString(data?.event)
}

function visibleTextFromNestedPayload(payload: Record<string, unknown> | null) {
  if (!payload) {
    return null
  }
  const text = asString(payload.text)
  if (text) {
    return text
  }
  const content = asRecord(payload.content)
  const contentPreview = textSummaryPreview(content)
  if (contentPreview) {
    return contentPreview
  }
  const recentMessages = Array.isArray(payload.recent_messages)
    ? payload.recent_messages
    : []
  for (const message of [...recentMessages].reverse()) {
    const summary = asRecord(message)
    const messageContent = asRecord(summary?.content)
    const preview = textSummaryPreview(messageContent)
    if (preview) {
      return preview
    }
  }
  return null
}

function summarizeValuesPayload(payload: Record<string, unknown> | null) {
  if (!payload) {
    return null
  }
  const structuredResponse = asRecord(payload.structured_response)
  if (structuredResponse) {
    const keys = Object.keys(structuredResponse)
    const chunks = asRecord(structuredResponse.chunk_ids)
    const candidates = asRecord(structuredResponse.edge_candidate_ids)
    const count =
      asNumber(chunks?.count) ??
      asNumber(candidates?.count)
    return count !== null
      ? `structured response (${keys.join(', ')}, ${count} ids)`
      : `structured response (${keys.join(', ')})`
  }
  const messageCount = asNumber(payload.message_count)
  const recentMessages = Array.isArray(payload.recent_messages)
    ? payload.recent_messages
    : []
  const latest = asRecord(recentMessages.at(-1))
  const latestType = asString(latest?.type) ?? 'message'
  const latestName = asString(latest?.name)
  return messageCount !== null
    ? `${messageCount} messages, latest ${latestName ?? latestType}`
    : null
}

function summarizeMessagePayload(payload: Record<string, unknown> | null) {
  if (!payload) {
    return null
  }
  const eventName = readNestedEventName(payload)
  const toolCall = asRecord(payload.tool_call)
  if (toolCall) {
    const toolName = asString(toolCall.name) ?? 'tool'
    return `${eventName ?? 'tool-call'} ${toolName}`
  }
  const usage = asRecord(payload.usage)
  const totalTokens = asNumber(usage?.total_tokens)
  if (eventName === 'message-finish' && totalTokens !== null) {
    return `message-finish (${totalTokens} tokens)`
  }
  const text = visibleTextFromNestedPayload(payload)
  if (text) {
    return `model text: ${text}`
  }
  return eventName
}

function textSummaryPreview(value: Record<string, unknown> | null) {
  if (!value) {
    return null
  }
  return (
    asString(value.preview) ??
    asString(value.text) ??
    asString(value.content) ??
    null
  )
}

function subroutineKeyFromPayload(payload: Record<string, unknown>) {
  return (
    asString(payload.chunk_id) ??
    asString(payload.document_id) ??
    asString(asRecord(payload.context)?.chunk_id) ??
    asString(asRecord(payload.context)?.document_id) ??
    asString(payload.agentName) ??
    undefined
  )
}

function resolveTopologyNode(stage: unknown, agentName: unknown): TopologyNodeId | null {
  if (isTopologyNodeId(stage)) {
    return stage
  }

  const normalizedAgentName = asString(agentName)?.toLowerCase() ?? ''
  if (normalizedAgentName.includes('chunk')) {
    return 'chunking_agent'
  }
  if (normalizedAgentName.includes('candidate')) {
    return 'graph_candidate_agent'
  }

  return null
}

function resolveTopologyEdge(edge: unknown): TopologyEdgeId | null {
  return isTopologyEdgeId(edge) ? edge : null
}

function isTopologyNodeId(value: unknown): value is TopologyNodeId {
  return (
    value === 'document_constructed' ||
    value === 'task_queue' ||
    value === 'chunking_agent' ||
    value === 'embedding_dispatch' ||
    value === 'graph_candidate_agent' ||
    value === 'edge_materializer' ||
    value === 'completed'
  )
}

function isTopologyEdgeId(value: unknown): value is TopologyEdgeId {
  return (
    value === 'queue_to_worker' ||
    value === 'doc_to_queue' ||
    value === 'queue_to_chunk' ||
    value === 'chunk_to_embed' ||
    value === 'embed_to_candidate' ||
    value === 'build_result_to_job_state' ||
    value === 'review_result_to_job_state' ||
    value === 'materializer_to_completed'
  )
}
