import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Cpu,
  FileText,
  GitBranch,
  ChevronRight,
  Copy,
  Check,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import {
  getJobProgress,
  getJobRuntimeStatus,
  getJobTaskTiming,
  getRuntimeStatusLabel,
  pipelineSteps,
  type JobRuntimeStatus,
} from '@/features/jobs/job-progress'
import { cn } from '@/lib/utils'
import type { FileIngestStatusResponse } from '@/types'

type JobCardProps = {
  job: FileIngestStatusResponse
  onClick?: () => void
}

export function JobCard({ job, onClick }: JobCardProps) {
  const progress = getJobProgress(job)
  const runtimeStatus = getJobRuntimeStatus(job)

  const [copied, setCopied] = useState(false)
  const [nowMs, setNowMs] = useState(0)
  const taskTiming = getJobTaskTiming(job, nowMs)

  useEffect(() => {
    const updateClock = () => setNowMs(Date.now())
    const timeout = window.setTimeout(updateClock, 0)

    if (!taskTiming.isLive) {
      return () => window.clearTimeout(timeout)
    }

    const interval = window.setInterval(updateClock, 1000)
    return () => {
      window.clearTimeout(timeout)
      window.clearInterval(interval)
    }
  }, [taskTiming.isLive])

  const handleCopyId = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(job.job_id)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClick?.()
        }
      }}
      className={cn(
        "w-full grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)] xl:grid-cols-[minmax(0,1.55fr)_minmax(0,2.7fr)_minmax(0,1.85fr)_minmax(0,1fr)] items-center gap-4 border border-border/45 bg-card/75 backdrop-blur-lg rounded-xl p-3 px-5 transition-all duration-300 hover:border-accent/35 hover:bg-muted/10 hover:shadow-[0_4px_20px_oklch(var(--color-accent)/6%)] hover:-translate-y-[1px] group/job focus-visible:ring-1 focus-visible:ring-accent/45 focus-visible:outline-none relative overflow-hidden select-none"
      )}
    >
      {/* 1. Left: Document Identity & Mini Copy Chip (22% Width) */}
      <div className="flex items-center gap-3 min-w-0 select-none">
        {getStatusAvatar(runtimeStatus)}
        <div className="min-w-0">
          <h4 className="truncate text-xs font-black text-foreground group-hover/job:text-accent transition-colors duration-300 leading-tight">
            {job.file_name}
          </h4>
          <div className="flex items-center gap-1 mt-1">
            <span className="text-[8px] text-muted-foreground/60 font-bold tracking-wide uppercase truncate max-w-[130px]">
              ID: {job.job_id} {job.document_id ? `| DOC: ${job.document_id}` : ''}
            </span>
            <button
              onClick={handleCopyId}
              className="p-0.5 rounded hover:bg-muted/65 text-muted-foreground/40 hover:text-foreground transition-all duration-200"
              title="Copy Job ID"
            >
              {copied ? (
                <Check className="size-2 text-green-500 stroke-[3.5]" />
              ) : (
                <Copy className="size-2" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 2. Center: Apple-style Premium Node Trail (38% Width) */}
      <div className="w-full min-w-0 select-none relative py-3 px-1.5 max-md:my-1">
        <div className="absolute top-[22px] left-[10px] right-[10px] h-0.5 bg-border/25 rounded-full z-0" />

        {/* Active Gradient Rail */}
        <div
          className="absolute top-[22px] left-[10px] h-0.5 bg-gradient-to-r from-primary via-accent to-secondary rounded-full transition-all duration-500 z-0"
          style={{
            width: `${Math.max(0, Math.min(100, ((progress.stepIndex - 1) / (pipelineSteps.length - 1)) * 100))}%`
          }}
        />

        <div className="relative z-10 flex items-center justify-between">
          {pipelineSteps.map((step, idx) => {
            const stepTargetIndex = {
              staged: 1,
              chunked: 2,
              built: 3,
              review: 4,
              complete: 5,
            }[step.key]

            const done = progress.stepIndex > stepTargetIndex
            const active = progress.stepIndex === stepTargetIndex
            const isFailed = active && runtimeStatus === 'needs_retry'

            return (
              <div key={step.key} className="flex flex-col items-center select-none group/node relative">
                <div
                  className={cn(
                    "size-5.5 rounded-full flex items-center justify-center border text-[8.5px] font-black transition-all duration-300 relative z-10 bg-card",
                    done
                      ? "bg-primary border-primary text-primary-foreground shadow-[0_1px_4px_oklch(var(--color-primary)/25%)]"
                      : active
                      ? isFailed
                        ? "bg-destructive border-destructive text-destructive-foreground animate-pulse"
                        : "bg-accent border-accent text-accent-foreground animate-pulse-ring"
                      : "border-border text-muted-foreground/35 hover:border-muted-foreground/50 hover:text-muted-foreground"
                  )}
                >
                  {done ? (
                    <Check className="size-2.5 stroke-[3.5]" />
                  ) : isFailed ? (
                    <AlertTriangle className="size-2.5" />
                  ) : (
                    <span>{idx + 1}</span>
                  )}
                </div>
                <span
                  className={cn(
                    "absolute top-6.5 text-[8px] font-black tracking-tight text-center leading-none whitespace-nowrap transition-colors duration-300",
                    active
                      ? isFailed
                        ? "text-destructive"
                        : "text-accent"
                      : done
                      ? "text-foreground/80"
                      : "text-muted-foreground/35 group-hover/node:text-muted-foreground/75"
                  )}
                >
                  {step.label}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* 3. Right Center: Custom Translucent Neon Metrics Capsules (26% Width) in Grid */}
      <div className="grid grid-cols-4 gap-1.5 w-full min-w-0 justify-items-stretch lg:col-start-1 xl:col-start-auto">
        <JobMetricInline
          icon={FileText}
          label="Chunks"
          value={job.chunk_count ?? 0}
          className="bg-amber-500/5 text-amber-700 dark:text-amber-400 border-amber-500/10 hover:bg-amber-500/10 hover:border-amber-500/25 w-full"
        />
        <JobMetricInline
          icon={GitBranch}
          label="Candidates"
          value={job.candidate_count ?? 0}
          className="bg-accent/5 text-accent border-accent/10 hover:bg-accent/10 hover:border-accent/25 w-full"
        />
        <JobMetricInline
          icon={Clock3}
          label="Review"
          value={job.pending_review_count ?? 0}
          className="bg-secondary/10 text-secondary-foreground border-secondary/15 hover:bg-secondary/15 hover:border-secondary/35 w-full"
        />
        <JobMetricInline
          icon={Cpu}
          label="Stages"
          value={job.stages.length}
          className="bg-cyan-500/5 text-cyan-700 dark:text-cyan-400 border-cyan-500/10 hover:bg-cyan-500/10 hover:border-cyan-500/25 w-full"
        />
      </div>

      {/* 4. Right: Action, Status Indicator & Pulse Chevron (14% Width) */}
      <div className="flex min-w-0 items-center justify-between gap-2 w-full lg:col-start-2 xl:col-start-auto pl-1">
        <div className="flex flex-col items-start gap-0.5 select-none text-[10.5px] text-left">
          <div className="flex items-center gap-1 font-bold text-foreground/80">
            <span className="shrink-0 animate-pulse text-accent">●</span>
            <span className="truncate font-black">{progress.label}</span>
          </div>
          <Badge
            variant={getStatusBadgeVariant(runtimeStatus)}
            className={cn(
              "font-black text-[7.5px] px-1.5 py-0 h-4 rounded-full select-none shrink-0 uppercase leading-none border",
              runtimeStatus === 'running'
                ? "bg-accent/10 text-accent border-accent/20"
                : runtimeStatus === 'complete'
                ? "bg-primary/8 text-primary border-primary/20"
                : runtimeStatus === 'waiting_review'
                ? "bg-secondary/15 text-secondary-foreground border-secondary/25"
                : runtimeStatus === 'needs_retry'
                ? "bg-destructive/10 text-destructive border-destructive/20 animate-pulse"
                : "bg-muted text-muted-foreground/75 border-border/50"
            )}
          >
            {getRuntimeStatusLabel(runtimeStatus)}
          </Badge>
          <span
            className={cn(
              "max-w-28 truncate rounded border px-1.5 py-0.5 text-[8px] font-black uppercase leading-none",
              taskTiming.isLive
                ? "border-accent/20 bg-accent/8 text-accent"
                : "border-border/60 bg-muted/25 text-muted-foreground/80",
            )}
            title={`${taskTiming.primaryLabel} · ${taskTiming.detailLabel}`}
          >
            {taskTiming.primaryLabel}
          </span>
        </div>

        <div className="p-1 rounded-full border border-border/25 bg-muted/10 text-muted-foreground/35 group-hover/job:text-accent group-hover/job:border-accent/25 group-hover/job:bg-accent/5 transition-all duration-300 ml-auto shrink-0">
          <ChevronRight className="size-3.5 group-hover/job:translate-x-0.5 transition-transform duration-300" />
        </div>
      </div>

      {job.warning ? (
        <div className="col-span-full mt-1 border-t border-dashed border-destructive/10 pt-1.5 flex items-center gap-1.5 text-[9px] text-destructive/75 font-bold select-none leading-none">
          <AlertTriangle className="size-2.5 shrink-0 text-destructive/80" aria-hidden="true" />
          <span className="truncate">{job.warning}</span>
        </div>
      ) : null}
    </div>
  )
}

function getStatusAvatar(status: JobRuntimeStatus) {
  switch (status) {
    case 'running':
      return (
        <div className="relative flex size-8.5 shrink-0 items-center justify-center rounded-xl bg-accent/10 border border-accent/20 text-accent transition-all duration-300">
          <div className="absolute inset-0 rounded-xl border border-dashed border-accent animate-spin [animation-duration:12s]" />
          <FileText className="size-4 animate-pulse text-accent" />
        </div>
      )
    case 'queued':
      return (
        <div className="relative flex size-8.5 shrink-0 items-center justify-center rounded-xl bg-muted/40 border border-border/40 text-muted-foreground transition-all duration-300">
          <div className="absolute inset-0 rounded-xl border border-dashed border-muted-foreground/35 animate-pulse" />
          <Clock3 className="size-4 text-muted-foreground/50" />
        </div>
      )
    case 'waiting_review':
      return (
        <div className="relative flex size-8.5 shrink-0 items-center justify-center rounded-xl bg-secondary/15 border border-secondary/25 text-secondary-foreground shadow-[0_0_8px_oklch(var(--color-secondary)/25%)] transition-all duration-300 animate-pulse">
          <div className="absolute inset-0 rounded-xl border border-secondary/35 animate-pulse-ring" />
          <AlertTriangle className="size-4 text-secondary-foreground" />
        </div>
      )
    case 'needs_retry':
      return (
        <div className="relative flex size-8.5 shrink-0 items-center justify-center rounded-xl bg-destructive/10 border border-destructive/20 text-destructive shadow-[0_0_8px_oklch(var(--color-destructive)/20%)] transition-all duration-300 animate-pulse">
          <FileText className="size-4 text-destructive" />
        </div>
      )
    case 'complete':
    default:
      return (
        <div className="relative flex size-8.5 shrink-0 items-center justify-center rounded-xl bg-primary/8 border border-primary/10 text-primary transition-all duration-300">
          <div className="absolute inset-[-1px] rounded-xl border border-primary/20 bg-primary/5 opacity-0 group-hover/job:opacity-100 transition-opacity duration-300" />
          <CheckCircle2 className="size-4 text-primary" />
        </div>
      )
  }
}

function JobMetricInline({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon: LucideIcon
  label: string
  value: number
  className?: string
}) {
  return (
    <span className={cn(
      "inline-flex items-center justify-center gap-1 px-1 py-0.5 rounded-full border text-[8.5px] font-black select-none transition-all duration-300 w-full truncate",
      className
    )}>
      <Icon className="size-2.5 opacity-60 shrink-0" aria-hidden="true" />
      <span className="truncate">{label}</span>
      <span className={cn(
        "font-black ml-0.5 shrink-0",
        value > 0 ? "opacity-100" : "opacity-50"
      )}>{value}</span>
    </span>
  )
}

function getStatusBadgeVariant(status: JobRuntimeStatus) {
  if (status === 'needs_retry') {
    return 'destructive'
  }
  if (status === 'complete') {
    return 'secondary'
  }

  return 'outline'
}
