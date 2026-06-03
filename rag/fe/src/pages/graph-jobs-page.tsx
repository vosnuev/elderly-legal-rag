import {
  CheckCircle2,
  Clock3,
  Cpu,
  GitBranch,
  Rows3,
  Terminal,
  Activity,
  Brain,
  Wrench,
  AlertTriangle,
  Circle,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'

import { JobCard } from '@/features/jobs/job-card'
import { Badge } from '@/components/ui/badge'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  getJobPhase,
  getJobProgress,
  getJobRuntimeStatus,
  getJobTaskTiming,
  pipelineSteps,
  isPipelineStepDone,
} from '@/features/jobs/job-progress'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'
import {
  useEventStreamer,
  type StreamEventLog,
} from '@/features/jobs/use-event-streamer'
import { cn } from '@/lib/utils'
import type { FileIngestStatusResponse } from '@/types'

type TerminalFilter = 'all' | 'agent' | 'tool' | 'service' | 'error'

const terminalFilters: TerminalFilter[] = ['all', 'agent', 'tool', 'service', 'error']

export function GraphJobsPage() {
  const { jobs, refresh, status } = useRagWorkspace()
  const terminalBottomRef = useRef<HTMLDivElement | null>(null)

  // Track selected job context for deep diagnostic visual popup
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const selectedJob = useMemo(
    () => jobs.find((job) => job.job_id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  )
  const [terminalFilter, setTerminalFilter] = useState<TerminalFilter>('all')
  const [selectedSubroutineKey, setSelectedSubroutineKey] = useState<string | null>(null)
  const [nowMs, setNowMs] = useState(0)

  // Selected job only: Redis SSE exposes internal agent/tool/service events.
  const {
    activeEdge,
    activeNode,
    activeTasks,
    logs,
    queueCount,
    streamStatus,
    workerLane,
  } = useEventStreamer(selectedJobId)

  // 3-Second Active Auto Poller (Keep synced with core API)
  useEffect(() => {
    const hasActiveJobs = jobs.some((job) => {
      const runStatus = getJobRuntimeStatus(job)
      return runStatus === 'running' || runStatus === 'queued'
    })

    if (!hasActiveJobs || status === 'loading') {
      return
    }

    const interval = setInterval(() => {
      void refresh()
    }, 3000)

    return () => clearInterval(interval)
  }, [jobs, refresh, status])

  const [activeStatusFilter, setActiveStatusFilter] = useState<'all' | 'running' | 'waiting_review' | 'complete'>('all')

  const filteredJobs = useMemo(() => {
    if (activeStatusFilter === 'all') {
      return jobs
    }
    return jobs.filter((job) => getJobRuntimeStatus(job) === activeStatusFilter)
  }, [jobs, activeStatusFilter])

  const runningCount = useMemo(() => jobs.filter(j => getJobRuntimeStatus(j) === 'running').length, [jobs])
  const reviewCount = useMemo(() => jobs.filter(j => getJobRuntimeStatus(j) === 'waiting_review').length, [jobs])
  const completeCount = useMemo(() => jobs.filter(j => getJobRuntimeStatus(j) === 'complete').length, [jobs])

  const runningJobsList = useMemo(() => jobs.filter((job) => getJobRuntimeStatus(job) === 'running'), [jobs])
  const failedJobsList = useMemo(() => jobs.filter((job) => getJobRuntimeStatus(job) === 'needs_retry'), [jobs])
  const reviewJobsList = useMemo(() => jobs.filter((job) => getJobRuntimeStatus(job) === 'waiting_review'), [jobs])

  const runningJobsCount = runningJobsList.length
  const reviewJobsCount = reviewJobsList.length

  const phaseBuckets = useMemo(() => getPipelinePhaseBuckets(jobs), [jobs])
  const pendingReviewCount = jobs.reduce(
    (total, job) => total + (job.pending_review_count ?? 0),
    0,
  )

  // Compute Overall Scheduler Activity Status
  const schedulerStatus = useMemo(() => {
    if (runningJobsCount > 0) return 'active'
    if (failedJobsList.length > 0) return 'stalled'
    if (reviewJobsCount > 0) return 'paused'
    return 'idle'
  }, [runningJobsCount, failedJobsList, reviewJobsCount])

  const schedulerMeta = useMemo(() => {
    switch (schedulerStatus) {
      case 'active':
        return {
          label: 'Active',
          styles: 'bg-chart-3/10 text-chart-3 border-chart-3/20 shadow-[0_0_12px_oklch(var(--color-chart-3)/10%)]',
          dot: 'bg-chart-3 animate-ping',
        }
      case 'stalled':
        return {
          label: 'Stalled',
          styles: 'bg-destructive/10 text-destructive border-destructive/20 shadow-[0_0_12px_oklch(var(--color-destructive)/10%)]',
          dot: 'bg-destructive animate-pulse',
        }
      case 'paused':
        return {
          label: 'Paused',
          styles: 'bg-primary/10 text-primary border-primary/20 shadow-[0_0_12px_oklch(var(--color-primary)/10%)]',
          dot: 'bg-primary animate-pulse',
        }
      default:
        return {
          label: 'Idle Standby',
          styles: 'bg-muted-foreground/10 text-muted-foreground border-border',
          dot: 'bg-muted-foreground',
        }
    }
  }, [schedulerStatus])

  // Current active step label for selected job inside modal.
  const selectedJobProgress = selectedJob ? getJobProgress(selectedJob) : null
  const selectedJobTiming = selectedJob ? getJobTaskTiming(selectedJob, nowMs) : null
  const subroutineFilters = useMemo(() => getSubroutineFilters(logs), [logs])
  const filteredLogs = useMemo(
    () => filterTerminalLogs(logs, terminalFilter, selectedSubroutineKey),
    [logs, selectedSubroutineKey, terminalFilter],
  )

  useEffect(() => {
    terminalBottomRef.current?.scrollIntoView({ block: 'end' })
  }, [filteredLogs.length, selectedJobId, selectedSubroutineKey, terminalFilter])

  useEffect(() => {
    const updateClock = () => setNowMs(Date.now())
    const timeout = window.setTimeout(updateClock, 0)

    if (!selectedJobTiming?.isLive) {
      return () => window.clearTimeout(timeout)
    }

    const interval = window.setInterval(updateClock, 1000)
    return () => {
      window.clearTimeout(timeout)
      window.clearInterval(interval)
    }
  }, [selectedJobTiming?.isLive])

  const openDiagnostics = (jobId: string) => {
    setSelectedJobId(jobId)
    setSelectedSubroutineKey(null)
    setTerminalFilter('all')
  }

  const closeDiagnostics = () => {
    setSelectedJobId(null)
    setSelectedSubroutineKey(null)
    setTerminalFilter('all')
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-5">
      {/* 1. Header of Ingestion Controller (Clean & borderless) */}
      <div className="flex items-center justify-between gap-3 select-none mt-1">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-black uppercase tracking-widest text-muted-foreground/80">Pipeline Overview</h3>
          <Badge variant="secondary" className={cn("font-black px-2 py-0.5 rounded-full text-[8.5px] uppercase tracking-wider border shrink-0 flex items-center gap-1.5 transition-all duration-300 select-none", schedulerMeta.styles)}>
            <span className={cn("size-1.5 rounded-full", schedulerMeta.dot)} />
            {schedulerMeta.label}
          </Badge>
        </div>
      </div>

      {/* 2. 5-Phase Pipeline HUD Track (Ultra-Slim Cards) */}
      <div className="grid gap-2.5 grid-cols-1 sm:grid-cols-5 select-none">
        <PhaseBucketCard
          icon={Rows3}
          label="Task queue"
          value={phaseBuckets.taskQueue}
          detail="queued"
          href="/documents"
        />
        <PhaseBucketCard
          icon={Cpu}
          label="Chunk phase"
          value={phaseBuckets.chunkPhase}
          detail="chunk/embed"
          tone="primary"
          onClick={() => setActiveStatusFilter('running')}
        />
        <PhaseBucketCard
          icon={GitBranch}
          label="Candidates"
          value={phaseBuckets.candidateExtraction}
          detail="agent runs"
          tone="chart"
          onClick={() => setActiveStatusFilter('all')}
        />
        <PhaseBucketCard
          icon={Clock3}
          label="Ready review"
          value={phaseBuckets.readyReview}
          detail={pendingReviewCount > 0 ? `${pendingReviewCount} candidates` : "pending jobs"}
          tone="review"
          onClick={() => setActiveStatusFilter('waiting_review')}
          action={
            <a
              href="/review-queue"
              className="h-5 rounded bg-destructive !text-white hover:bg-destructive/90 text-[8px] font-black uppercase tracking-wider px-1.5 transition-all duration-200 flex items-center justify-center cursor-pointer shadow-sm shadow-destructive/10 border border-transparent shrink-0"
            >
              Open
            </a>
          }
        />
        <PhaseBucketCard
          icon={CheckCircle2}
          label="Complete"
          value={phaseBuckets.complete}
          detail="finished"
          tone="complete"
          onClick={() => setActiveStatusFilter('complete')}
        />
      </div>

      {/* Main Document Processing Queue List */}
      <section className="mt-1.5 flex min-h-0 flex-1 flex-col gap-3.5 border border-border/40 bg-card/45 backdrop-blur-md rounded-2xl p-5 select-none">
        <div className="flex flex-wrap items-center justify-between gap-4 select-none pb-2 border-b border-border/25">
          <div>
            <h3 className="text-sm font-black tracking-tight text-foreground">Document Processing Queue</h3>
            <p className="mt-0.5 text-[10.5px] text-muted-foreground/80 font-bold">
              Each document job exposes status, phase, review counts, and a live diagnostics stream.
            </p>
          </div>

          {/* Status Filter Tab Row */}
          <div className="flex flex-wrap items-center gap-1 bg-muted/40 p-0.5 rounded-lg border border-border/20">
            <button
              onClick={() => setActiveStatusFilter('all')}
              className={cn(
                "h-6.5 rounded-md px-2.5 text-[9px] font-black uppercase tracking-wider transition-all duration-300 flex items-center gap-1.5 cursor-pointer",
                activeStatusFilter === 'all'
                  ? "bg-card text-foreground shadow-[0_1px_3px_rgba(0,0,0,0.05)] border border-border/20"
                  : "text-muted-foreground/60 hover:text-foreground hover:bg-muted/30"
              )}
            >
              All
              <span className={cn(
                "px-1 py-0.2 rounded-full text-[7.5px] font-black",
                activeStatusFilter === 'all' ? "bg-primary/10 text-primary" : "bg-muted-foreground/10 text-muted-foreground/70"
              )}>{jobs.length}</span>
            </button>

            <button
              onClick={() => setActiveStatusFilter('running')}
              className={cn(
                "h-6.5 rounded-md px-2.5 text-[9px] font-black uppercase tracking-wider transition-all duration-300 flex items-center gap-1.5 cursor-pointer",
                activeStatusFilter === 'running'
                  ? "bg-accent text-accent-foreground shadow-[0_2px_8px_oklch(var(--color-accent)/20%)]"
                  : "text-muted-foreground/60 hover:text-foreground hover:bg-muted/30"
              )}
            >
              <span className={cn("size-1.5 rounded-full shrink-0", activeStatusFilter === 'running' ? "bg-accent-foreground animate-ping" : "bg-accent")} />
              Running
              <span className={cn(
                "px-1 py-0.2 rounded-full text-[7.5px] font-black",
                activeStatusFilter === 'running' ? "bg-accent-foreground/20 text-accent-foreground" : "bg-accent/10 text-accent"
              )}>{runningCount}</span>
            </button>

            <button
              onClick={() => setActiveStatusFilter('waiting_review')}
              className={cn(
                "h-6.5 rounded-md px-2.5 text-[9px] font-black uppercase tracking-wider transition-all duration-300 flex items-center gap-1.5 cursor-pointer",
                activeStatusFilter === 'waiting_review'
                  ? "bg-secondary text-secondary-foreground shadow-[0_2px_8px_oklch(var(--color-secondary)/20%)]"
                  : "text-muted-foreground/60 hover:text-foreground hover:bg-muted/30"
              )}
            >
              <span className={cn("size-1.5 rounded-full shrink-0", activeStatusFilter === 'waiting_review' ? "bg-secondary-foreground animate-pulse" : "bg-secondary-foreground/65")} />
              Waiting Review
              <span className={cn(
                "px-1 py-0.2 rounded-full text-[7.5px] font-black",
                activeStatusFilter === 'waiting_review' ? "bg-secondary-foreground/20 text-secondary-foreground" : "bg-secondary/15 text-secondary-foreground"
              )}>{reviewCount}</span>
            </button>

            <button
              onClick={() => setActiveStatusFilter('complete')}
              className={cn(
                "h-6.5 rounded-md px-2.5 text-[9px] font-black uppercase tracking-wider transition-all duration-300 flex items-center gap-1.5 cursor-pointer",
                activeStatusFilter === 'complete'
                  ? "bg-primary text-primary-foreground shadow-[0_1px_3px_rgba(0,0,0,0.05)]"
                  : "text-muted-foreground/60 hover:text-foreground hover:bg-muted/30"
              )}
            >
              <span className={cn("size-1.5 rounded-full shrink-0", activeStatusFilter === 'complete' ? "bg-primary-foreground animate-pulse" : "bg-primary")} />
              Complete
              <span className={cn(
                "px-1 py-0.2 rounded-full text-[7.5px] font-black",
                activeStatusFilter === 'complete' ? "bg-primary-foreground/20 text-primary-foreground" : "bg-primary/10 text-primary"
              )}>{completeCount}</span>
            </button>
          </div>
        </div>

        {/* Dedicated Sleek Scroll viewport for documents list */}
        <div className="min-h-0 flex-1 overflow-y-auto pr-1 space-y-2.5
          [&::-webkit-scrollbar]:w-1.5
          [&::-webkit-scrollbar-track]:bg-muted/10
          [&::-webkit-scrollbar-track]:rounded-full
          [&::-webkit-scrollbar-thumb]:bg-primary/15
          [&::-webkit-scrollbar-thumb]:rounded-full
          hover:[&::-webkit-scrollbar-thumb]:bg-primary/35
          scroll-smooth pt-1.5"
        >
          {filteredJobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed border-border/50 rounded-xl bg-muted/5 select-none">
              <span className="text-xl">📭</span>
              <p className="mt-2 text-xs font-black text-muted-foreground/65">No documents match the selected filter.</p>
              <button
                onClick={() => setActiveStatusFilter('all')}
                className="mt-3.5 h-6 rounded-md border border-border/75 bg-card hover:bg-muted/20 px-3 text-[9px] font-black uppercase tracking-wider cursor-pointer"
              >
                Clear Filter
              </button>
            </div>
          ) : (
            filteredJobs.map((job) => (
              <JobCard
                key={job.job_id}
                job={job}
                onClick={() => openDiagnostics(job.job_id)}
              />
            ))
          )}
        </div>
      </section>

      {/* Advanced Deep Diagnostics Studio Modal (Job Selected Context) */}
      <Dialog open={Boolean(selectedJob)} onOpenChange={(open) => !open && closeDiagnostics()}>
        <DialogContent className="sm:max-w-[98vw] xl:max-w-[104rem] h-[94vh] flex flex-col border border-primary/10 shadow-2xl rounded-2xl bg-card/95 backdrop-blur-md overflow-hidden p-0 animate-scale-up">
          <DialogHeader className="p-6 pb-4.5 bg-muted/15 border-b border-border/45 flex flex-row items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <div className="flex size-9.5 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary shadow-sm">
                <Brain className="size-5 animate-pulse" />
              </div>
              <div className="min-w-0">
                <DialogTitle className="text-base font-extrabold tracking-tight text-foreground truncate max-w-[18rem] sm:max-w-[28rem]">
                  {selectedJob?.file_name}
                </DialogTitle>
                <DialogDescription className="text-[10px] font-semibold text-muted-foreground/80 mt-1 select-none">
                  Diagnostics Studio • Ingest ID: {selectedJob?.job_id}
                </DialogDescription>
              </div>
            </div>
            {selectedJobProgress && (
              <Badge variant="secondary" className="font-black px-2 py-0.5 rounded-md text-[9px] bg-primary/10 text-primary border border-primary/20 leading-none shrink-0 select-none mr-4">
                {selectedJobProgress.label}
              </Badge>
            )}
          </DialogHeader>

          <div className="flex-1 min-h-0 overflow-hidden grid gap-4 p-5 sm:grid-cols-[minmax(0,1fr)_minmax(13.5rem,0.24fr)]">
            <div className="min-h-0 flex flex-col gap-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2 select-none shrink-0">
                <div>
                  <p className="text-[9.5px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1">
                    Agent Terminal
                  </p>
                  <p className="mt-1 text-[10px] font-bold text-muted-foreground/70 pl-1">
                    {filteredLogs.length} events · {subroutineFilters.length} routines
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-1.5">
                  {terminalFilters.map((filter) => (
                    <button
                      key={filter}
                      type="button"
                      onClick={() => setTerminalFilter(filter)}
                      className={cn(
                        "h-6 rounded-md border px-2 text-[8.5px] font-black uppercase tracking-widest transition-colors",
                        terminalFilter === filter
                          ? "border-primary/35 bg-primary/10 text-primary"
                          : "border-border/70 bg-muted/20 text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {filter}
                    </button>
                  ))}
                </div>
              </div>

              {subroutineFilters.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1.5 select-none">
                  <button
                    type="button"
                    onClick={() => setSelectedSubroutineKey(null)}
                    className={cn(
                      "h-6 rounded-md border px-2 text-[8.5px] font-black uppercase tracking-widest transition-colors",
                      selectedSubroutineKey === null
                        ? "border-primary/35 bg-primary/10 text-primary"
                        : "border-border/70 bg-muted/20 text-muted-foreground hover:text-foreground",
                    )}
                  >
                    all routines
                  </button>
                  {subroutineFilters.map((filter) => (
                    <button
                      key={filter.key}
                      type="button"
                      onClick={() => setSelectedSubroutineKey(filter.key)}
                      className={cn(
                        "h-6 rounded-md border px-2 text-[8.5px] font-black uppercase tracking-widest transition-colors",
                        selectedSubroutineKey === filter.key
                          ? filter.tone.badge
                          : "border-border/70 bg-muted/20 text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {filter.label}
                      <span className="ml-1 opacity-70">{filter.count}</span>
                    </button>
                  ))}
                </div>
              ) : null}

              <ScrollArea className="flex-1 min-h-[28rem] sm:min-h-0 rounded-xl border border-primary/10 bg-black/92 p-5 focus-within:ring-1 focus-within:ring-primary/45 transition-all shadow-inner">
                <div className="font-mono text-[10.5px] space-y-3">
                  {filteredLogs.length > 0 ? (
                    filteredLogs.map((log) => {
                      const isAgent = log.type === 'agent'
                      const isService = log.type === 'service'
                      const isError = log.type === 'error'
                      const tone = getSubroutineTone(log)

                      return (
                        <div key={log.id} className={cn("flex flex-col gap-2 leading-relaxed transition-all duration-300 animate-slide-in border-b border-white/5 pb-3 pl-3 border-l-2", tone.border)}>
                          <div className="flex items-start gap-2.5">
                            <span className="text-slate-500 shrink-0 select-none font-bold">
                              [{log.timestamp}]
                            </span>
                            <span className={cn(
                              "font-black uppercase tracking-wider text-[8px] px-1.5 py-0.5 rounded-sm select-none shrink-0 leading-none mt-0.5",
                              isAgent
                                ? "bg-sky-500/20 text-sky-300 border border-sky-500/30"
                                : isService
                                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                  : isError
                                    ? "bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse"
                                    : "bg-white/10 text-white/70 border border-white/5"
                            )}>
                              {isAgent ? 'AGENT' : isService ? 'SERVICE' : isError ? 'ERR' : 'LIFE'}
                            </span>

                            {isAgent && log.agentName && (
                              <Badge variant="outline" className={cn("text-[8.5px] font-black tracking-wider px-1.5 py-0 rounded leading-none shrink-0 uppercase select-none", tone.badge)}>
                                {log.agentName}
                              </Badge>
                            )}

                            {isService && log.serviceName && (
                              <Badge variant="outline" className="text-[8.5px] font-black tracking-wider border-emerald-500/30 bg-emerald-500/10 text-emerald-400 px-1.5 py-0 rounded leading-none shrink-0 uppercase select-none">
                                {log.serviceName}
                              </Badge>
                            )}

                            {log.streamChannel ? (
                              <Badge variant="outline" className="text-[8px] font-black tracking-wider border-white/10 bg-white/5 text-white/55 px-1.5 py-0 rounded leading-none shrink-0 uppercase select-none">
                                {log.streamChannel}
                              </Badge>
                            ) : null}

                            {log.subroutineKey ? (
                              <Badge variant="outline" className={cn("max-w-36 truncate text-[8px] font-black tracking-wider px-1.5 py-0 rounded leading-none shrink-0 uppercase select-none", tone.badge)}>
                                {getSubroutineLabel(log.subroutineKey)}
                              </Badge>
                            ) : null}

                            {log.eventName ? (
                              <Badge variant="outline" className="text-[8px] font-black tracking-wider border-white/10 bg-white/5 text-white/45 px-1.5 py-0 rounded leading-none shrink-0 select-none">
                                {log.eventName}
                              </Badge>
                            ) : null}

                            <span className={cn(
                              "flex-1 break-words font-semibold",
                              isError ? "text-rose-400" : "text-slate-100"
                            )}>
                              {log.text}
                            </span>
                          </div>

                          {isAgent && log.thought && (
                            <AgentOutputFoldout value={log.thought} />
                          )}

                          {isAgent && log.toolUsage && (
                            <div className="ml-8 border border-teal-500/20 bg-slate-900/60 backdrop-blur-sm rounded-xl p-3.5 space-y-2 select-text shadow-sm shadow-teal-500/5 animate-scale-up">
                              <div className="flex items-center gap-1.5 text-[8.5px] font-black text-teal-400 uppercase tracking-widest leading-none select-none">
                                <Wrench className="size-3.5" />
                                Tool call: {log.toolUsage.name}
                              </div>
                              <PayloadFoldout
                                label="Arguments payload"
                                tone="teal"
                                value={JSON.stringify(log.toolUsage.arguments, null, 2)}
                              />
                              {log.toolUsage.result ? (
                                <PayloadFoldout
                                  label="Result payload"
                                  tone="emerald"
                                  value={formatToolResult(log.toolUsage.result)}
                                />
                              ) : null}
                            </div>
                          )}

                          {isError && (
                            <div className="ml-8 border border-rose-500/20 bg-rose-950/20 rounded-xl p-3 flex items-start gap-2.5 animate-pulse select-none">
                              <AlertTriangle className="size-4.5 text-rose-400 shrink-0 mt-0.5" />
                              <div className="space-y-1">
                                <p className="text-[8.5px] font-black text-rose-400 uppercase tracking-widest leading-none">Stream diagnostic</p>
                                <p className="text-[10px] text-rose-300/90 font-bold leading-normal">
                                  Check backend event stream availability and job status polling.
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })
                  ) : (
                    <div className="flex flex-col items-center justify-center h-48 text-slate-600 text-xs select-none gap-2">
                      <Terminal className="size-5" />
                      <span>Awaiting document queue transaction stream...</span>
                    </div>
                  )}
                  <div ref={terminalBottomRef} />
                </div>
              </ScrollArea>
            </div>

            {selectedJob && (
              <aside className="min-h-0 rounded-xl border border-border/60 bg-muted/10 p-4 select-none flex flex-col gap-3 overflow-hidden">
                <div className="grid gap-2 rounded-lg border border-border/50 bg-background/35 p-3">
                  <StreamMetric label="Stream" value={streamStatus} />
                  <StreamMetric label="Queue" value={`${queueCount} waiting`} />
                  <StreamMetric label="Active tasks" value={String(activeTasks)} />
                  <StreamMetric label="Lane" value={workerLane ?? 'none'} />
                  <StreamMetric label="Node" value={activeNode ?? 'none'} />
                  <StreamMetric label="Edge" value={activeEdge ?? 'none'} />
                  {selectedJobTiming ? (
                    <>
                      <StreamMetric label="Runtime" value={selectedJobTiming.runtimeLabel} />
                      <StreamMetric label="Queue wait" value={selectedJobTiming.queueWaitLabel} />
                      <StreamMetric label="Picked up" value={selectedJobTiming.startedLabel} />
                      <StreamMetric label="Finished" value={selectedJobTiming.finishedLabel} />
                    </>
                  ) : null}
                </div>

                <div className="min-h-0 rounded-lg border border-border/50 bg-background/35 p-3 overflow-auto">
                  <p className="text-[9.5px] font-black text-muted-foreground uppercase tracking-widest leading-none">
                    Graph Step
                  </p>
                  <div className="mt-3 grid gap-2">
                    {pipelineSteps.map((step) => {
                      const done = isPipelineStepDone(selectedJob, step.key)
                      const isCurrent = selectedJobProgress?.label.toLowerCase() === step.label.toLowerCase() ||
                        (step.key === 'staged' && selectedJobProgress?.label.toLowerCase() === 'queued')

                      return (
                        <div
                          key={step.key}
                          className={cn(
                            'flex min-h-9 items-center gap-2 rounded-lg border px-3 text-xs font-bold transition-all duration-300',
                            done
                              ? 'border-primary/20 bg-primary/8 text-primary font-extrabold'
                              : isCurrent
                                ? 'border-primary/30 bg-primary/5 text-primary animate-pulse'
                                : 'border-border/60 bg-muted/35 text-muted-foreground/70',
                          )}
                        >
                          {done ? (
                            <CheckCircle2 className="size-3.5 shrink-0 text-primary" aria-hidden="true" />
                          ) : isCurrent ? (
                            <Activity className="size-3.5 shrink-0 text-primary animate-pulse" aria-hidden="true" />
                          ) : (
                            <Circle className="size-3.5 shrink-0 text-muted-foreground/45" aria-hidden="true" />
                          )}
                          <span className="truncate">{step.label}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </aside>
            )}
          </div>

          <div className="p-4 px-6.5 bg-muted/15 border-t border-border/45 flex justify-end shrink-0 select-none">
            <button
              type="button"
              onClick={closeDiagnostics}
              className="text-xs font-bold px-5 h-8.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/95 shadow-sm transition-all cursor-pointer"
            >
              Close Diagnostics Studio
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function getPipelinePhaseBuckets(jobs: FileIngestStatusResponse[]) {
  const buckets = {
    candidateExtraction: 0,
    chunkPhase: 0,
    complete: 0,
    readyReview: 0,
    taskQueue: 0,
  }

  for (const job of jobs) {
    const runtimeStatus = getJobRuntimeStatus(job)
    const phase = getJobPhase(job).toLowerCase()

    if (runtimeStatus === 'complete' || job.completed) {
      buckets.complete += 1
    } else if (runtimeStatus === 'waiting_review' || phase.includes('pending_review')) {
      buckets.readyReview += 1
    } else if (job.current_task?.status === 'queued') {
      buckets.taskQueue += 1
    } else if (
      phase.includes('candidate') ||
      phase.includes('graph') ||
      phase.includes('embedding_dispatched')
    ) {
      buckets.candidateExtraction += 1
    } else {
      buckets.chunkPhase += 1
    }
  }

  return buckets
}

function PhaseBucketCard({
  action,
  detail,
  extra,
  icon: Icon,
  label,
  tone = 'neutral',
  value,
  onClick,
  href,
}: {
  action?: React.ReactNode
  detail: string
  extra?: React.ReactNode
  icon: LucideIcon
  label: string
  tone?: 'neutral' | 'primary' | 'chart' | 'review' | 'complete'
  value: number
  onClick?: () => void
  href?: string
}) {
  const toneClass = {
    chart: 'border-chart-2/20 bg-chart-2/5 text-chart-2 shadow-[0_1px_4px_oklch(var(--color-chart-2)/4%)]',
    complete: 'border-emerald-500/25 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400 shadow-[0_1px_4px_rgba(16,185,129,0.08)]',
    neutral: 'border-border/60 bg-muted/20 text-foreground/85',
    primary: 'border-primary/20 bg-primary/5 text-primary shadow-[0_1px_4px_oklch(var(--color-primary)/4%)]',
    review: 'border-destructive/20 bg-destructive/5 text-destructive shadow-[0_1px_4px_oklch(var(--color-destructive)/4%)]',
  }[tone]

  const Component = href ? 'a' : 'div'

  return (
    <Component
      href={href}
      onClick={onClick}
      className={cn(
        "h-13 rounded-xl border p-2 px-3 transition-all duration-300 hover:-translate-y-[0.5px] hover:shadow-[0_2px_8px_rgba(0,0,0,0.02)] flex items-center justify-between gap-3 select-none",
        toneClass,
        (onClick || href) && "cursor-pointer hover:border-current/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-current"
      )}
      {...((onClick || href) ? { role: 'button', tabIndex: 0 } : {})}
      onKeyDown={(e) => {
        if ((onClick || href) && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault()
          if (href) {
            window.location.href = href
          } else {
            onClick?.()
          }
        }
      }}
    >
      <div className="min-w-0 flex items-center gap-2">
        <div className="p-1 rounded bg-background/30 text-current shrink-0">
          <Icon className="size-3.5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <p className="text-[10.5px] font-black leading-none truncate">{label}</p>
          <p className="mt-0.5 text-[8px] font-black uppercase tracking-wider opacity-60 leading-none truncate">{detail}</p>
        </div>
      </div>

      {extra && <div className="hidden lg:flex items-center shrink-0">{extra}</div>}

      <div className="flex items-center gap-2 shrink-0">
        {action && <div className="shrink-0" onClick={(e) => e.stopPropagation()}>{action}</div>}
        <Badge variant="outline" className="h-4.5 rounded-md bg-background/50 px-2 text-[9.5px] font-black border-current/10 shrink-0 leading-none flex items-center justify-center">
          {value}
        </Badge>
      </div>
    </Component>
  )
}

function StreamMetric({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="flex items-center justify-between gap-3 text-[10px] font-bold">
      <span className="text-muted-foreground uppercase tracking-widest">{label}</span>
      <span className="truncate text-foreground/90">{value}</span>
    </div>
  )
}

function filterTerminalLogs(
  logs: StreamEventLog[],
  filter: TerminalFilter,
  subroutineKey: string | null,
) {
  const bySubroutine = subroutineKey
    ? logs.filter((log) => log.subroutineKey === subroutineKey)
    : logs

  switch (filter) {
    case 'agent':
      return bySubroutine.filter((log) => log.type === 'agent')
    case 'error':
      return bySubroutine.filter((log) => log.type === 'error')
    case 'service':
      return bySubroutine.filter((log) => log.type === 'service' || log.type === 'lifecycle')
    case 'tool':
      return bySubroutine.filter((log) => Boolean(log.toolUsage) || log.streamChannel === 'tools' || log.streamChannel === 'tool_calls')
    case 'all':
      return bySubroutine
  }
}

function getSubroutineFilters(logs: StreamEventLog[]) {
  const counts = new Map<string, number>()
  for (const log of logs) {
    if (!log.subroutineKey || isStreamNodeKey(log.subroutineKey)) {
      continue
    }
    counts.set(log.subroutineKey, (counts.get(log.subroutineKey) ?? 0) + 1)
  }

  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 12)
    .map(([key, count]) => ({
      count,
      key,
      label: getSubroutineLabel(key),
      tone: getToneForSubroutineKey(key),
    }))
}

function isStreamNodeKey(key: string) {
  return ['model', 'tool', 'tools', 'messages', 'values'].includes(key.toLowerCase())
}

function getSubroutineLabel(key: string) {
  if (key.length <= 12) {
    return key
  }
  return `${key.slice(0, 6)}..${key.slice(-4)}`
}

function getSubroutineTone(log: StreamEventLog) {
  return getToneForSubroutineKey(log.subroutineKey ?? log.agentName ?? log.type)
}

function formatToolResult(result: string) {
  try {
    return JSON.stringify(JSON.parse(result), null, 2)
  } catch {
    return result
  }
}

function AgentOutputFoldout({ value }: { value: string }) {
  return (
    <details className="group ml-8 border border-sky-500/20 bg-slate-900/60 backdrop-blur-sm rounded-xl p-3.5 select-text shadow-sm shadow-sky-500/5 animate-scale-up">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[8.5px] font-black text-sky-400 uppercase tracking-widest leading-none select-none [&::-webkit-details-marker]:hidden">
        <span className="flex min-w-0 items-center gap-1.5">
          <Brain className="size-3.5 animate-pulse shrink-0" />
          <span>Agent output</span>
          <span className="max-w-[42rem] truncate text-[10px] normal-case tracking-normal text-slate-300/80 font-semibold">
            {summarizeTerminalText(value)}
          </span>
        </span>
        <span className="shrink-0 rounded border border-sky-500/20 bg-sky-500/10 px-1.5 py-0.5 text-[8px] text-sky-300">
          {value.length.toLocaleString()} chars
        </span>
      </summary>
      <pre className="mt-3 max-h-[28rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-sky-500/10 bg-black/40 p-3 text-[10px] text-slate-300 font-mono leading-relaxed">
        {value}
      </pre>
    </details>
  )
}

function PayloadFoldout({
  label,
  tone,
  value,
}: {
  label: string
  tone: 'teal' | 'emerald'
  value: string
}) {
  const toneClass = tone === 'teal' ? 'text-teal-300 border-teal-500/10' : 'text-emerald-300 border-emerald-500/10'
  return (
    <details className="group bg-black/40 rounded-lg p-2 border border-teal-500/10">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[8px] font-black text-slate-500 uppercase tracking-widest select-none [&::-webkit-details-marker]:hidden">
        <span>{label}</span>
        <span className="max-w-[44rem] truncate text-[9px] normal-case tracking-normal text-slate-400 font-semibold">
          {summarizeTerminalText(value, 160)}
        </span>
        <span className="shrink-0 rounded border border-white/10 bg-white/5 px-1.5 py-0.5 text-[8px] text-slate-400">
          {value.length.toLocaleString()} chars
        </span>
      </summary>
      <pre className={cn("mt-2 max-h-[28rem] overflow-auto whitespace-pre-wrap break-words rounded-md border bg-black/45 p-2 text-[9.5px] font-mono leading-relaxed", toneClass)}>
        {value}
      </pre>
    </details>
  )
}

function summarizeTerminalText(value: string, maxChars = 220) {
  const normalized = value.replace(/\s+/g, ' ').trim()
  if (normalized.length <= maxChars) {
    return normalized
  }
  return `${normalized.slice(0, maxChars)}...`
}

function getToneForSubroutineKey(key: string) {
  const tones = [
    {
      badge: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
      border: 'border-l-sky-500/45',
    },
    {
      badge: 'border-teal-500/30 bg-teal-500/10 text-teal-300',
      border: 'border-l-teal-500/45',
    },
    {
      badge: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
      border: 'border-l-violet-500/45',
    },
    {
      badge: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
      border: 'border-l-amber-500/45',
    },
    {
      badge: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
      border: 'border-l-emerald-500/45',
    },
  ]
  return tones[hashString(key) % tones.length]
}

function hashString(value: string) {
  let hash = 0
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0
  }
  return hash
}
