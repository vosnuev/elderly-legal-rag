import {
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
import { Progress } from '@/components/ui/progress'
import {
  formatStageName,
  getJobProgress,
  getJobRuntimeStatus,
  getRuntimeStatusLabel,
  getWorkerGroupLabel,
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
  const workerGroup = getWorkerGroupLabel(job)

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
      <CardHeader className="p-5 pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="truncate text-base font-extrabold tracking-tight group-hover/job:text-primary transition-colors duration-300">
              {job.file_name}
            </CardTitle>
            <p className="mt-1.5 text-[10px] text-muted-foreground/80 font-semibold tracking-wider uppercase">
              ID: {job.job_id}
              {job.document_id ? ` • DOC: ${job.document_id}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Badge variant={getStatusBadgeVariant(runtimeStatus)} className="font-bold rounded-full">
              {getRuntimeStatusLabel(runtimeStatus)}
            </Badge>
            <Badge variant="outline" className="font-bold rounded-full border-primary/20 bg-primary/5 text-primary">
              {workerGroup}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-5 p-5 pt-0">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2 text-sm">
              <span className="p-1 rounded-md bg-muted text-foreground/80 group-hover/job:bg-primary/10 group-hover/job:text-primary transition-all duration-300">
                {getStatusIcon(runtimeStatus)}
              </span>
              <span className="truncate font-bold text-foreground/90">{progress.label}</span>
              <span className="text-muted-foreground/70 text-xs font-semibold">/ {formatStageName(job.current_stage)}</span>
            </div>
            <span className="text-xs font-black text-primary bg-primary/5 px-2 py-0.5 rounded-md border border-primary/10">
              {progress.percent}%
            </span>
          </div>
          <Progress value={progress.percent} className="h-2 rounded-full overflow-hidden" />
        </div>

        <div className="grid gap-2.5 sm:grid-cols-4">
          <JobMetric icon={FileText} label="Chunks" value={job.chunk_count ?? 0} />
          <JobMetric icon={GitBranch} label="Candidates" value={job.candidate_count ?? 0} />
          <JobMetric icon={Clock3} label="Review Queue" value={job.pending_review_count ?? 0} />
          <JobMetric icon={Cpu} label="Total Stages" value={job.stages.length} />
        </div>

        {/* Pipeline Step visual flowchart */}
        <div className="grid gap-2 sm:grid-cols-5">
          {pipelineSteps.map((step) => {
            const done = isPipelineStepDone(job, step.key)

            return (
              <div
                key={step.key}
                className={cn(
                  'flex min-h-11 items-center gap-2.5 rounded-xl border px-3 text-xs font-bold transition-all duration-300 shadow-sm relative overflow-hidden',
                  done
                    ? 'border-primary/20 bg-gradient-to-r from-primary/10 to-chart-2/5 text-primary font-extrabold'
                    : 'border-border/60 bg-muted/40 text-muted-foreground/70',
                )}
              >
                {done && (
                  <span className="absolute top-0 left-0 h-full w-0.5 bg-primary" />
                )}
                {done ? (
                  <CheckCircle2 className="size-4 shrink-0 text-primary animate-pulse" aria-hidden="true" />
                ) : (
                  <Circle className="size-4 shrink-0 text-muted-foreground/50" aria-hidden="true" />
                )}
                <span className="truncate">{step.label}</span>
              </div>
            )
          })}
        </div>

        {job.warning ? (
          <p className="rounded-xl border border-dashed border-destructive/20 bg-destructive/5 px-3 py-2 text-xs leading-relaxed text-destructive/80 font-medium">
            ⚠️ {job.warning}
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}

function JobMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon
  label: string
  value: number
}) {
  return (
    <div className="flex min-w-0 items-center gap-3 rounded-xl border border-border/70 bg-muted/45 px-3.5 py-2.5 transition-all duration-300 hover:bg-primary/5 hover:border-primary/20 hover:translate-y-[-1px] group/metric">
      <div className="p-1.5 rounded-lg bg-card text-muted-foreground group-hover/metric:text-primary transition-colors duration-300">
        <Icon className="size-4 shrink-0" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-[10px] font-black text-muted-foreground/80 uppercase tracking-wider leading-none">
          {label}
        </p>
        <p className="mt-1 text-sm font-extrabold text-foreground/90">{value}</p>
      </div>
    </div>
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
    return <CheckCircle2 className="size-4 text-muted-foreground" aria-hidden="true" />
  }
  if (status === 'needs_retry') {
    return <RotateCcw className="size-4 text-muted-foreground" aria-hidden="true" />
  }

  return <Clock3 className="size-4 text-muted-foreground" aria-hidden="true" />
}
