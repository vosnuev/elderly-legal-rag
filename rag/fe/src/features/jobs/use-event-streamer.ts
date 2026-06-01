import { useEffect, useState, useRef } from 'react'

export interface StreamEventLog {
  id: string
  timestamp: string
  type: 'lifecycle' | 'message' | 'error' | 'agent' | 'service'
  text: string
  // Enhanced properties for beautiful transparency monitor
  agentName?: string
  thought?: string
  toolUsage?: {
    name: string
    arguments: Record<string, any>
    result?: string
  }
  serviceName?: string
}

export type TopologyNodeId =
  | 'document_constructed'
  | 'task_queue'
  | 'chunking_agent'
  | 'embedding_dispatch'
  | 'graph_candidate_agent'
  | 'candidate_revision_agent'
  | 'edge_materializer'
  | 'completed'

export type TopologyEdgeId =
  | 'doc_to_queue'
  | 'queue_to_chunk'
  | 'chunk_to_embed'
  | 'embed_to_candidate'
  | 'candidate_to_revision'
  | 'revision_to_materializer'
  | 'materializer_to_completed'

// Richly-structured 8 steps pipeline diagnostic steps
const demoFlowSteps = [
  {
    activeNode: 'document_constructed' as TopologyNodeId,
    activeEdge: 'doc_to_queue' as TopologyEdgeId,
    queueCount: 1,
    workerLoad: 15,
    logType: 'service' as const,
    serviceName: 'IngestProgressNodeService',
    logText: 'Document raw text received. Parsing payload characters and initializing metadata.',
  },
  {
    activeNode: 'task_queue' as TopologyNodeId,
    activeEdge: 'queue_to_chunk' as TopologyEdgeId,
    queueCount: 3,
    workerLoad: 35,
    logType: 'service' as const,
    serviceName: 'RedisQueueBroker',
    logText: 'Ingest pipeline job scheduled. Dispatching to ingest-workers worker lane.',
  },
  {
    activeNode: 'chunking_agent' as TopologyNodeId,
    activeEdge: 'chunk_to_embed' as TopologyEdgeId,
    queueCount: 2,
    workerLoad: 78,
    logType: 'agent' as const,
    agentName: 'ChunkingAgent',
    thought: '문서의 내용이 너무 길어 LLM 컨텍스트 윈도우 크기를 초과할 수 있습니다. 각 문단 간의 의미적 연속성(Semantic overlap)을 15%로 유지하면서, 최대 800토큰 크기의 16개 청크로 분할해야 합니다.',
    toolUsage: {
      name: 'semantic_text_splitter',
      arguments: { chunk_size: 800, chunk_overlap: 120, text_type: 'markdown' },
    },
    logText: 'Segmented document body into 16 discrete semantic paragraph tokens.',
  },
  {
    activeNode: 'embedding_dispatch' as TopologyNodeId,
    activeEdge: 'embed_to_candidate' as TopologyEdgeId,
    queueCount: 2,
    workerLoad: 95,
    logType: 'service' as const,
    serviceName: 'EmbeddingDispatchNodeService',
    logText: 'Initiating embedding vector generation. Dispatching 16 chunks concurrently to vector database.',
  },
  {
    activeNode: 'graph_candidate_agent' as TopologyNodeId,
    activeEdge: 'candidate_to_revision' as TopologyEdgeId,
    queueCount: 1,
    workerLoad: 85,
    logType: 'agent' as const,
    agentName: 'GraphCandidateAgent',
    thought: '추출된 청크 16개에서 핵심 엔티티(Entity) 간의 관계(Relation)를 분석해야 합니다. "OpenAI"와 "Microsoft"의 파트너십 선언 에지를 추출하고 이를 RDF 트리플 형식으로 보정하겠습니다.',
    toolUsage: {
      name: 'entity_extractor_tool',
      arguments: { max_entities: 25, confidence_threshold: 0.85, target_ontology: 'GraphRAG-Core' },
    },
    logText: 'Extracted 12 vertices and 8 semantic relation edges from vector chunks.',
  },
  {
    activeNode: 'candidate_revision_agent' as TopologyNodeId,
    activeEdge: 'revision_to_materializer' as TopologyEdgeId,
    queueCount: 1,
    workerLoad: 50,
    logType: 'agent' as const,
    agentName: 'GraphCandidateRevisionAgent',
    thought: '이전 단계에서 추출된 관계 데이터 중 중복되거나 신뢰도가 낮은 비정상 에지가 있는지 검증합니다. 2개의 중복 에지를 제거하고 Rationale 근거 사유를 정밀 보완하겠습니다.',
    toolUsage: {
      name: 'graph_anomaly_detector',
      arguments: { scan_duplicates: true, prune_dangling_nodes: true },
    },
    logText: 'Validated relationship constraints and anomaly ratios. Cleaned 2 redundant edges.',
  },
  {
    activeNode: 'edge_materializer' as TopologyNodeId,
    activeEdge: 'materializer_to_completed' as TopologyEdgeId,
    queueCount: 0,
    workerLoad: 65,
    logType: 'service' as const,
    serviceName: 'EdgeMaterializationNodeService',
    logText: 'Writing 8 verified semantic relation vertices into Neo4j graph storage and updating graph index metadata.',
  },
  {
    activeNode: 'completed' as TopologyNodeId,
    activeEdge: null,
    queueCount: 0,
    workerLoad: 0,
    logType: 'service' as const,
    serviceName: 'ArchiveSyncNodeService',
    logText: 'Pipeline transaction successfully completed and locked. Stored document ID: doc-924-f3a.',
  },
]

export function useEventStreamer(selectedJobId: string | null) {
  const [jobIndices, setJobIndices] = useState<Record<string, number>>({})
  const [jobLogs, setJobLogs] = useState<Record<string, StreamEventLog[]>>({})
  const [jobMetrics, setJobMetrics] = useState<Record<string, { queueCount: number; workerLoad: number }>>({})
  
  const [liveNodes, setLiveNodes] = useState<Record<string, TopologyNodeId | null>>({})
  const [liveEdges, setLiveEdges] = useState<Record<string, TopologyEdgeId | null>>({})

  const socketRef = useRef<WebSocket | null>(null)
  const isDemoActiveRef = useRef(true)

  const addLog = (
    jobId: string, 
    type: 'lifecycle' | 'message' | 'error' | 'agent' | 'service', 
    text: string,
    meta?: { agentName?: string; thought?: string; toolUsage?: any; serviceName?: string }
  ) => {
    const newLog: StreamEventLog = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString('ko-KR', { hour12: false }),
      type,
      text,
      ...meta,
    }
    setJobLogs((prev) => {
      const currentLogs = prev[jobId] ?? []
      return {
        ...prev,
        [jobId]: [newLog, ...currentLogs].slice(0, 15), // Extended to 15 logs
      }
    })
  }

  // WebSocket Live Stream Connector
  useEffect(() => {
    const wsUrl = `ws://${window.location.hostname}:8000/api/system/events/ws`
    const ws = new WebSocket(wsUrl)
    socketRef.current = ws

    ws.onopen = () => {
      isDemoActiveRef.current = false
      if (selectedJobId) {
        addLog(selectedJobId, 'lifecycle', 'System: Connected to live event streaming websocket.')
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const jobId = data.job_id ?? data.payload?.job_id
        
        if (!jobId) return

        if (data.channel === 'agent_transcript' && data.payload) {
          const payload = data.payload
          setLiveNodes((prev) => ({ ...prev, [jobId]: payload.stage as TopologyNodeId }))
          setLiveEdges((prev) => ({ ...prev, [jobId]: payload.edge as TopologyEdgeId }))
          
          if (payload.log) {
            const isAgent = payload.type === 'agent'
            const isService = payload.type === 'service'
            addLog(jobId, payload.type ?? 'message', payload.log, {
              agentName: isAgent ? payload.agentName : undefined,
              thought: isAgent ? payload.thought : undefined,
              toolUsage: isAgent ? payload.toolUsage : undefined,
              serviceName: isService ? payload.serviceName : undefined,
            })
          }
        }
        
        if (data.channel === 'worker_metrics' && data.payload) {
          setJobMetrics((prev) => ({
            ...prev,
            [jobId]: {
              queueCount: data.payload.queue_count ?? 0,
              workerLoad: data.payload.worker_load ?? 0,
            }
          }))
        }
      } catch (err) {
        // Skip corrupted socket packets
      }
    }

    ws.onerror = () => {
      if (!isDemoActiveRef.current) {
        isDemoActiveRef.current = true
        if (selectedJobId) {
          addLog(selectedJobId, 'error', 'System: Connection failed. Switching to multi-job simulator.')
        }
      }
    }

    ws.onclose = () => {
      if (!isDemoActiveRef.current) {
        isDemoActiveRef.current = true
        if (selectedJobId) {
          addLog(selectedJobId, 'lifecycle', 'System: Socket closed. Activating multi-job simulation.')
        }
      }
    }

    return () => {
      ws.close()
    }
  }, [selectedJobId])

  // Multi-Job Independent Simulation Timer
  useEffect(() => {
    if (!isDemoActiveRef.current || !selectedJobId) return

    // If no initial log exists for this Job ID, seed it
    if (!jobLogs[selectedJobId] || jobLogs[selectedJobId].length === 0) {
      addLog(selectedJobId, 'lifecycle', `System: Initializing diagnostics streaming context for Job ID [${selectedJobId}].`)
    }

    const timer = setInterval(() => {
      if (!isDemoActiveRef.current) return

      setJobIndices((prev) => {
        const currentIdx = prev[selectedJobId] ?? 0
        const nextIdx = (currentIdx + 1) % demoFlowSteps.length
        
        // Push step specific logs with rich structure
        const step = demoFlowSteps[nextIdx]
        addLog(selectedJobId, step.logType, step.logText, {
          agentName: step.agentName,
          thought: step.thought,
          toolUsage: step.toolUsage,
          serviceName: step.serviceName,
        })
        
        return {
          ...prev,
          [selectedJobId]: nextIdx,
        }
      })
    }, 4000)

    return () => clearInterval(timer)
  }, [selectedJobId, jobLogs])

  // Extract variables based on the currently selected Document Job Context
  const currentStepIndex = selectedJobId ? (jobIndices[selectedJobId] ?? 0) : 0
  const activeStep = demoFlowSteps[currentStepIndex]

  const activeNode = selectedJobId 
    ? (isDemoActiveRef.current ? activeStep.activeNode : (liveNodes[selectedJobId] ?? null))
    : null
    
  const activeEdge = selectedJobId
    ? (isDemoActiveRef.current ? activeStep.activeEdge : (liveEdges[selectedJobId] ?? null))
    : null

  const queueCount = selectedJobId
    ? (isDemoActiveRef.current ? activeStep.queueCount : (jobMetrics[selectedJobId]?.queueCount ?? 0))
    : 0

  const workerLoad = selectedJobId
    ? (isDemoActiveRef.current ? activeStep.workerLoad : (jobMetrics[selectedJobId]?.workerLoad ?? 0))
    : 0

  const logs = selectedJobId ? (jobLogs[selectedJobId] ?? []) : []

  return {
    activeNode,
    activeEdge,
    queueCount,
    workerLoad,
    logs,
  }
}
