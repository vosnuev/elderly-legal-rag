import {
  CheckCircle2,
  Clock3,
  Cpu,
  GitBranch,
  Rows3,
  Sparkles,
  Terminal,
  Activity,
  Brain,
  Wrench,
  AlertTriangle,
  Circle,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { JobCard } from '@/features/jobs/job-card'
import { PageHeader } from '@/components/workspace/page-header'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  getJobProgress,
  getJobRuntimeStatus,
  getWorkerGroupLabel,
  pipelineSteps,
  isPipelineStepDone,
  type WorkerGroupKey,
} from '@/features/jobs/job-progress'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'
import { useEventStreamer } from '@/features/jobs/use-event-streamer'
import { cn } from '@/lib/utils'
import type { FileIngestStatusResponse } from '@/types'

export function GraphJobsPage() {
  const { jobs, refresh, status } = useRagWorkspace()
  
  // Track selected job context for deep diagnostic visual popup
  const [selectedJob, setSelectedJob] = useState<FileIngestStatusResponse | null>(null)
  
  const selectedJobId = selectedJob?.job_id ?? null

  // Real-time Event Streaming & Demo Hook targeted for the selected Job ID
  const { queueCount, workerLoad, logs } = useEventStreamer(selectedJobId)

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

  // Sync selected job data when workspace refresh happens
  useEffect(() => {
    if (selectedJob) {
      const updated = jobs.find(j => j.job_id === selectedJob.job_id)
      if (updated) {
        setSelectedJob(updated)
      }
    }
  }, [jobs, selectedJob])

  const runningJobsList = useMemo(() => jobs.filter((job) => getJobRuntimeStatus(job) === 'running'), [jobs])
  const queuedJobsList = useMemo(() => jobs.filter((job) => getJobRuntimeStatus(job) === 'queued'), [jobs])
  const failedJobsList = useMemo(() => jobs.filter((job) => getJobRuntimeStatus(job) === 'needs_retry'), [jobs])
  const reviewJobsList = useMemo(() => jobs.filter((job) => getJobRuntimeStatus(job) === 'waiting_review'), [jobs])

  const runningJobsCount = runningJobsList.length
  const queuedJobsCount = queuedJobsList.length
  const reviewJobsCount = reviewJobsList.length

  const workerGroupCounts = getWorkerGroupCounts(jobs)
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

  // Current active step percent for selected job inside modal
  const selectedJobProgress = selectedJob ? getJobProgress(selectedJob) : null

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Graph Jobs"
        description="Track graph-add dispatch, worker groups, and document-level processing progress."
        action={
          <div className="flex flex-wrap gap-2 select-none">
            <Badge variant="outline">{jobs.length} documents</Badge>
            <Badge variant="secondary">{pendingReviewCount} review candidates</Badge>
          </div>
        }
      />

      {/* Main Overall System Situation Board */}
      <div className="grid items-start gap-3 xl:grid-cols-[minmax(0,1.25fr)_minmax(22rem,0.75fr)]">
        {/* Left: System Situation Overall Board */}
        <Card className="border border-border/80 bg-card/65 backdrop-blur-md rounded-2xl relative overflow-hidden transition-all duration-300">
          <div className="absolute top-0 left-0 h-[3px] w-full bg-gradient-to-r from-primary via-chart-2 to-primary opacity-40" />
          <CardHeader className="p-6 pb-3 border-b border-border/10 bg-muted/5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base font-extrabold tracking-tight">System Situation Board</CardTitle>
                <CardDescription className="text-xs text-muted-foreground mt-1 select-none">
                  Redis 큐 대기열, 워커 레인의 가동 분담률 및 인제스트/검수 대기 문서 현황판입니다.
                </CardDescription>
              </div>
              <Badge variant="secondary" className={cn("font-black px-2.5 py-1 rounded-md text-[9px] uppercase tracking-wider border shrink-0 flex items-center gap-1.5 transition-all duration-300 select-none", schedulerMeta.styles)}>
                <span className={cn("size-2 rounded-full", schedulerMeta.dot)} />
                {schedulerMeta.label}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-6 grid gap-5 select-none">
            <div className="grid gap-4.5 sm:grid-cols-2">
              {/* Worker Group Active Allocation */}
              <div className="border border-border/60 bg-muted/15 rounded-xl p-4.5 space-y-3.5">
                <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1">
                  Worker Allocation Load
                </p>
                <div className="space-y-3">
                  <WorkerMiniLoad label="ingest-workers" value={workerGroupCounts['ingest-workers']} max={5} />
                  <WorkerMiniLoad label="chunk-workers" value={workerGroupCounts['chunk-workers']} max={5} color="bg-primary" />
                  <WorkerMiniLoad label="graph-builders" value={workerGroupCounts['graph-builders']} max={5} color="bg-chart-2" />
                  <WorkerMiniLoad label="review-handoff" value={pendingReviewCount} max={12} color="bg-destructive" />
                  <WorkerMiniLoad label="archive-sync" value={workerGroupCounts['archive-sync']} max={5} color="bg-chart-3" />
                </div>
              </div>

              {/* Active & Pending Queue Status */}
              <div className="border border-border/60 bg-muted/15 rounded-xl p-4.5 flex flex-col justify-between">
                <div>
                  <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1 mb-3.5">
                    Pipeline Operational Backlogs
                  </p>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs font-bold p-2 bg-background/55 rounded-lg border border-border/40">
                      <span className="flex items-center gap-1.5 text-foreground/80">
                        <Activity className="size-3.5 text-primary animate-pulse" />
                        진행 중인 작업 (Active)
                      </span>
                      <Badge variant="outline" className="font-extrabold text-[10px] text-primary border-primary/20 bg-primary/5">
                        {runningJobsCount + queuedJobsCount} files
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-xs font-bold p-2 bg-background/55 rounded-lg border border-border/40">
                      <span className="flex items-center gap-1.5 text-foreground/80">
                        <Clock3 className="size-3.5 text-destructive animate-pulse" />
                        수동 검수 대기 (Review)
                      </span>
                      <Badge variant="outline" className={cn(
                        "font-extrabold text-[10px] border-destructive/20 bg-destructive/5 text-destructive",
                        reviewJobsCount > 0 ? "animate-pulse" : ""
                      )}>
                        {reviewJobsCount} jobs
                      </Badge>
                    </div>
                  </div>
                </div>

                <div className="border-t border-border/20 pt-3 mt-3 flex items-center justify-between text-[10px] text-muted-foreground/60 font-bold">
                  <span>Backlog Lock status</span>
                  <span className="text-foreground/90 font-black">UNLOCKED / Standby</span>
                </div>
              </div>
            </div>

            {/* Quick Helper Summary Bar */}
            <div className="border border-border/40 bg-muted/5 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs select-none">
              <span className="text-muted-foreground/80 font-bold flex items-center gap-1.5">
                <Sparkles className="size-3.5 text-primary animate-pulse shrink-0" />
                인제스트 목록에서 문서를 클릭하시면 **5단계 Graph Step**과 AI 에이전트의 **도구 사용/생각과정(Transparency)**을 심층 진단할 수 있습니다.
              </span>
              <Badge variant="outline" className="text-[9px] font-black border-primary/10">diagnostics active</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Right: Worker Groups Stats Widget */}
        <Card className="border border-border/80 bg-card/65 backdrop-blur-md rounded-2xl transition-all duration-300">
          <CardHeader className="p-6 pb-4">
            <CardTitle className="text-base font-extrabold tracking-tight">Worker Groups</CardTitle>
            <CardDescription className="text-xs text-muted-foreground mt-1 select-none">Queue pressure by processing lane.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2 p-6 pt-0 select-none">
            <WorkerGroupRow
              icon={Rows3}
              label="ingest-workers"
              value={workerGroupCounts['ingest-workers']}
              detail="queued documents"
            />
            <WorkerGroupRow
              icon={Cpu}
              label="chunk-workers"
              value={workerGroupCounts['chunk-workers']}
              detail="active documents"
            />
            <WorkerGroupRow
              icon={GitBranch}
              label="graph-builders"
              value={workerGroupCounts['graph-builders']}
              detail="graph-add jobs"
            />
            <WorkerGroupRow
              icon={Clock3}
              label="review-handoff"
              value={pendingReviewCount}
              detail="candidate decisions"
            />
            <WorkerGroupRow
              icon={CheckCircle2}
              label="archive-sync"
              value={workerGroupCounts['archive-sync']}
              detail="completed documents"
            />
          </CardContent>
        </Card>
      </div>

      {/* Main Document Processing Queue List */}
      <section className="grid gap-3 mt-1.5">
        <div className="flex flex-wrap items-end justify-between gap-2 select-none">
          <div>
            <h3 className="text-sm font-semibold">Document Processing Queue</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Progress is shown per document so parallel workers can be audited independently.
            </p>
          </div>
          <Badge variant="outline">{runningJobsCount + queuedJobsCount} active</Badge>
        </div>
        {jobs.map((job) => (
          <JobCard 
            key={job.job_id} 
            job={job} 
            onClick={() => setSelectedJob(job)} 
          />
        ))}
      </section>

      {/* Advanced Deep Diagnostics Studio Modal (Job Selected Context) */}
      <Dialog open={Boolean(selectedJob)} onOpenChange={(open) => !open && setSelectedJob(null)}>
        <DialogContent className="sm:max-w-4xl max-h-[88vh] flex flex-col border border-primary/10 shadow-2xl rounded-2xl bg-card/95 backdrop-blur-md overflow-hidden p-0 animate-scale-up">
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
                Step progress: {selectedJobProgress.percent}%
              </Badge>
            )}
          </DialogHeader>

          <div className="flex-1 min-h-0 overflow-y-auto p-6.5 space-y-6">
            {/* A. Graph Current Step (5-stage Timeline flowchart) */}
            {selectedJob && (
              <div className="flex flex-col gap-2.5 bg-muted/10 border border-border/50 rounded-xl p-4.5 select-none">
                <p className="text-[9.5px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1">
                  Graph Ingestion Current Step
                </p>
                <div className="grid gap-2 sm:grid-cols-5 mt-1.5">
                  {pipelineSteps.map((step) => {
                    const done = isPipelineStepDone(selectedJob, step.key)
                    const isCurrent = selectedJobProgress?.label.toLowerCase() === step.label.toLowerCase() || 
                                      (step.key === 'staged' && selectedJobProgress?.label.toLowerCase() === 'queued')

                    return (
                      <div
                        key={step.key}
                        className={cn(
                          'flex min-h-11 items-center gap-2.5 rounded-xl border px-3 text-xs font-bold transition-all duration-300 shadow-sm relative overflow-hidden',
                          done
                            ? 'border-primary/20 bg-gradient-to-r from-primary/10 to-chart-2/5 text-primary font-extrabold'
                            : isCurrent
                              ? 'border-primary/30 bg-primary/5 text-primary animate-pulse'
                              : 'border-border/60 bg-muted/40 text-muted-foreground/70',
                        )}
                      >
                        {done && (
                          <span className="absolute top-0 left-0 h-full w-0.5 bg-primary" />
                        )}
                        {done ? (
                          <CheckCircle2 className="size-4 shrink-0 text-primary" aria-hidden="true" />
                        ) : isCurrent ? (
                          <Activity className="size-4 shrink-0 text-primary animate-pulse" aria-hidden="true" />
                        ) : (
                          <Circle className="size-4 shrink-0 text-muted-foreground/45" aria-hidden="true" />
                        )}
                        <span className="truncate">{step.label}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Micro Load Metric panel inside modal */}
            <div className="grid gap-4.5 sm:grid-cols-2 select-none">
              <div className="border border-border/60 bg-muted/20 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none">
                    Job Queue Backlog
                  </p>
                  <p className="text-2xl font-black text-foreground mt-2 leading-none">{queueCount} waiting</p>
                </div>
                <Badge variant="outline" className="text-[8.5px] border-primary/20">Redis Queue</Badge>
              </div>

              <div className="border border-border/60 bg-muted/20 rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none">
                  <span>Worker Thread Load</span>
                  <span className="text-primary">{workerLoad}%</span>
                </div>
                <Progress value={workerLoad} className="h-1.5 rounded-full overflow-hidden" />
              </div>
            </div>

            {/* B. Transparancy Event Terminal Console */}
            <div className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between select-none">
                <p className="text-[9.5px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1">
                  Transparency Event Terminal Console
                </p>
                <Badge variant="outline" className="font-bold text-[8.5px] rounded-md border-border/80 uppercase tracking-widest text-muted-foreground">
                  Socket Stream: Active
                </Badge>
              </div>

              <ScrollArea className="h-[20rem] rounded-xl border border-primary/10 bg-black/90 p-5 focus-within:ring-1 focus-within:ring-primary/45 transition-all shadow-inner">
                <div className="font-mono text-[10.5px] space-y-3.5">
                  {logs.length > 0 ? (
                    logs.map((log) => {
                      const isAgent = log.type === 'agent'
                      const isService = log.type === 'service'
                      const isError = log.type === 'error'

                      return (
                        <div key={log.id} className="flex flex-col gap-2 leading-relaxed transition-all duration-300 animate-slide-in border-b border-white/5 pb-3">
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
                              <Badge variant="outline" className="text-[8.5px] font-black tracking-wider border-sky-500/30 bg-sky-500/10 text-sky-400 px-1.5 py-0 rounded leading-none shrink-0 uppercase select-none">
                                🤖 {log.agentName}
                              </Badge>
                            )}
                            
                            {isService && log.serviceName && (
                              <Badge variant="outline" className="text-[8.5px] font-black tracking-wider border-emerald-500/30 bg-emerald-500/10 text-emerald-400 px-1.5 py-0 rounded leading-none shrink-0 uppercase select-none">
                                ⚙️ {log.serviceName}
                              </Badge>
                            )}

                            <span className={cn(
                              "flex-1 break-all font-semibold",
                              isError ? "text-rose-400" : "text-slate-100"
                            )}>
                              {log.text}
                            </span>
                          </div>

                          {/* Render beautiful Agent thoughts if available */}
                          {isAgent && log.thought && (
                            <div className="ml-8 border border-sky-500/20 bg-slate-900/60 backdrop-blur-sm rounded-xl p-3.5 space-y-2 select-text shadow-sm shadow-sky-500/5 animate-scale-up">
                              <div className="flex items-center gap-1.5 text-[8.5px] font-black text-sky-400 uppercase tracking-widest leading-none select-none">
                                <Brain className="size-3.5 animate-pulse" />
                                Agent Diagnostic Thought Process
                              </div>
                              <p className="text-[10px] text-slate-300 leading-relaxed font-semibold italic">
                                "{log.thought}"
                              </p>
                            </div>
                          )}

                          {/* Render beautiful MCP Tool Usage with formatted JSON if available */}
                          {isAgent && log.toolUsage && (
                            <div className="ml-8 border border-teal-500/20 bg-slate-900/60 backdrop-blur-sm rounded-xl p-3.5 space-y-2 select-text shadow-sm shadow-teal-500/5 animate-scale-up">
                              <div className="flex items-center gap-1.5 text-[8.5px] font-black text-teal-400 uppercase tracking-widest leading-none select-none">
                                <Wrench className="size-3.5" />
                                🔧 MCP Tool Invocated: {log.toolUsage.name}
                              </div>
                              <div className="bg-black/40 rounded-lg p-2 border border-teal-500/10">
                                <p className="text-[8px] font-black text-slate-500 uppercase tracking-widest mb-1 select-none">Arguments payload</p>
                                <pre className="text-[9.5px] text-teal-300 font-mono leading-relaxed truncate">
                                  {JSON.stringify(log.toolUsage.arguments, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}

                          {/* Render beautiful service warning / error panel */}
                          {isError && (
                            <div className="ml-8 border border-rose-500/20 bg-rose-950/20 rounded-xl p-3 flex items-start gap-2.5 animate-pulse select-none">
                              <AlertTriangle className="size-4.5 text-rose-400 shrink-0 mt-0.5" />
                              <div className="space-y-1">
                                <p className="text-[8.5px] font-black text-rose-400 uppercase tracking-widest leading-none">Diagnostic Crash Report</p>
                                <p className="text-[10px] text-rose-300/90 font-bold leading-normal">
                                  Pipeline process halted during stage verification. Awaiting worker rescheduling loop.
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
                </div>
              </ScrollArea>
            </div>
          </div>

          <div className="p-4 px-6.5 bg-muted/15 border-t border-border/45 flex justify-end shrink-0 select-none">
            <button
              type="button"
              onClick={() => setSelectedJob(null)}
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

function getWorkerGroupCounts(jobs: FileIngestStatusResponse[]) {
  const counts: Record<WorkerGroupKey, number> = {
    'ingest-workers': 0,
    'chunk-workers': 0,
    'graph-builders': 0,
    'review-handoff': 0,
    'archive-sync': 0,
  }

  for (const job of jobs) {
    counts[getWorkerGroupLabel(job)] += 1
  }

  return counts
}

function WorkerMiniLoad({
  label,
  value,
  max,
  color = 'bg-chart-3',
}: {
  label: string
  value: number
  max: number
  color?: string
}) {
  const percentage = Math.min((value / max) * 100, 100)
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] font-bold text-foreground/80 leading-none">
        <span>{label}</span>
        <span className="text-muted-foreground/80">{value} / {max} active</span>
      </div>
      <div className="h-1.5 w-full bg-border/40 rounded-full overflow-hidden">
        <div className={cn("h-full transition-all duration-500 rounded-full", color, percentage > 0 ? "animate-pulse" : "")} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

function WorkerGroupRow({
  detail,
  icon: Icon,
  label,
  value,
}: {
  detail: string
  icon: LucideIcon
  label: string
  value: number
}) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 rounded-xl border border-border bg-muted/20 px-3.5 py-2.5 transition-all duration-300 hover:bg-primary/5 hover:border-primary/10">
      <div className="flex min-w-0 items-center gap-3">
        <Icon className="size-4 shrink-0 text-muted-foreground/60" aria-hidden="true" />
        <div className="min-w-0">
          <p className="truncate text-xs font-bold text-foreground/90">{label}</p>
          <p className="text-[10px] text-muted-foreground/60 leading-none mt-1">{detail}</p>
        </div>
      </div>
      <Badge variant={value > 0 ? 'outline' : 'secondary'} className={cn(
        "font-extrabold px-2 py-0.5 rounded-md text-[9px] tracking-wider leading-none",
        value > 0 ? "border-primary/20 bg-primary/5 text-primary" : ""
      )}>
        {value}
      </Badge>
    </div>
  )
}
