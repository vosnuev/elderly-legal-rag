import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Clock3,
  Cpu,
  FileText,
  GitBranch,
  type LucideIcon,
  RotateCcw,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  formatStageName,
  getJobPhase,
  getJobProgress,
  getJobRuntimeStatus,
  getRuntimeStatusLabel,
  isPipelineStepDone,
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
  const phaseLabel = formatStageName(getJobPhase(job))

  return (
    <Card 
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onClick?.()
        }
      }}
      size="sm" 
      className="cursor-pointer border border-border/80 bg-card/65 backdrop-blur-md rounded-2xl transition-all duration-300 hover:border-primary/25 hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-0.5 group/job focus-visible:ring-2 focus-visible:ring-primary/45 focus-visible:outline-none relative overflow-hidden"
    >
      <CardHeader className="p-4 pb-2.5 select-none">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <CardTitle className="truncate text-sm font-extrabold tracking-tight group-hover/job:text-primary transition-colors duration-300">
              {job.file_name}
            </CardTitle>
            <p className="mt-0.5 text-[9.5px] text-muted-foreground/80 font-bold tracking-wider uppercase">
              ID: {job.job_id}
              {job.document_id ? ` • DOC: ${job.document_id}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-1.5 shrink-0">
            <Badge variant={getStatusBadgeVariant(runtimeStatus)} className="font-bold text-[9px] px-2 py-0 h-5.5 rounded-full select-none">
              {getRuntimeStatusLabel(runtimeStatus)}
            </Badge>
            <Badge variant="outline" className="font-bold text-[9px] px-2 py-0 h-5.5 rounded-full border-primary/20 bg-primary/5 text-primary select-none">
              {phaseLabel}
            </Badge>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="grid gap-3.5 p-4 pt-0">
        {/* Row 2: Status Indicator & Compact Inline Metrics */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/15 pt-3">
          <div className="flex min-w-0 items-center gap-2 text-xs select-none">
            <span className="p-0.5 rounded-md bg-muted text-foreground/80 group-hover/job:bg-primary/10 group-hover/job:text-primary transition-all duration-300 shrink-0">
              {getStatusIcon(runtimeStatus)}
            </span>
            <span className="truncate font-extrabold text-foreground/90">{progress.label}</span>
            <span className="text-muted-foreground/60 text-[10px] font-bold shrink-0">/ {phaseLabel}</span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <JobMetricInline icon={FileText} label="Chunks" value={job.chunk_count ?? 0} />
            <JobMetricInline icon={GitBranch} label="Candidates" value={job.candidate_count ?? 0} />
            <JobMetricInline icon={Clock3} label="Review" value={job.pending_review_count ?? 0} />
            <JobMetricInline icon={Cpu} label="Stages" value={job.stages.length} />
          </div>
        </div>

        {/* Row 3: Pipeline Step visual flowchart (Ultra Compact) */}
        <div className="grid gap-1.5 grid-cols-5 mt-0.5">
          {pipelineSteps.map((step) => {
            const done = isPipelineStepDone(job, step.key)

            return (
              <div
                key={step.key}
                className={cn(
                  'flex h-7 items-center gap-1.5 rounded-lg border px-2 text-[10px] font-extrabold transition-all duration-300 shadow-sm relative overflow-hidden select-none',
                  done
                    ? 'border-primary/20 bg-gradient-to-r from-primary/10 to-chart-2/5 text-primary font-extrabold shadow-[0_1px_4px_oklch(var(--color-primary)/5%)]'
                    : 'border-border/50 bg-muted/30 text-muted-foreground/60',
                )}
              >
                {done && (
                  <span className="absolute top-0 left-0 h-full w-0.5 bg-primary" />
                )}
                {done ? (
                  <CheckCircle2 className="size-3 shrink-0 text-primary animate-pulse" aria-hidden="true" />
                ) : (
                  <Circle className="size-3 shrink-0 text-muted-foreground/30" aria-hidden="true" />
                )}
                <span className="truncate leading-none">{step.label}</span>
              </div>
            )
          })}
        </div>

        {job.warning ? (
          <p className="flex items-start gap-1.5 rounded-lg border border-dashed border-destructive/20 bg-destructive/5 px-2.5 py-1.5 text-[9.5px] leading-relaxed text-destructive/80 font-bold select-none">
            <AlertTriangle className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
            <span>{job.warning}</span>
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}

function JobMetricInline({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon
  label: string
  value: number
}) {
  return (
    <span className="inline-flex items-center gap-1 bg-muted/40 px-2 py-0.5 rounded-md border border-border/40 text-[10px] font-bold text-muted-foreground/80 select-none group/metric hover:bg-primary/5 hover:border-primary/20 transition-all duration-300">
      <Icon className="size-3 text-muted-foreground/70 group-hover/metric:text-primary transition-colors shrink-0" aria-hidden="true" />
      <span>{label}</span>
      <span className="text-foreground font-black ml-0.5">{value}</span>
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

function getStatusIcon(status: JobRuntimeStatus) {
  if (status === 'complete') {
    return <CheckCircle2 className="size-3 text-muted-foreground" aria-hidden="true" />
  }
  if (status === 'needs_retry') {
    return <RotateCcw className="size-3 text-muted-foreground animate-pulse" aria-hidden="true" />
  }

  return <Clock3 className="size-3 text-muted-foreground" aria-hidden="true" />
}
