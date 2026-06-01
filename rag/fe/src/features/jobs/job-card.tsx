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
}

export function JobCard({ job }: JobCardProps) {
  const progress = getJobProgress(job)
  const runtimeStatus = getJobRuntimeStatus(job)
  const workerGroup = getWorkerGroupLabel(job)

  return (
    <Card size="sm">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="truncate">{job.file_name}</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              {job.job_id}
              {job.document_id ? ` - ${job.document_id}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Badge variant={getStatusBadgeVariant(runtimeStatus)}>
              {getRuntimeStatusLabel(runtimeStatus)}
            </Badge>
            <Badge variant="outline">{workerGroup}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2 text-sm">
              {getStatusIcon(runtimeStatus)}
              <span className="truncate font-medium">{progress.label}</span>
              <span className="text-muted-foreground">/ {formatStageName(job.current_stage)}</span>
            </div>
            <span className="text-xs font-medium text-muted-foreground">{progress.percent}%</span>
          </div>
          <Progress value={progress.percent} />
        </div>

        <div className="grid gap-2 sm:grid-cols-4">
          <JobMetric icon={FileText} label="Chunks" value={job.chunk_count ?? 0} />
          <JobMetric icon={GitBranch} label="Candidates" value={job.candidate_count ?? 0} />
          <JobMetric icon={Clock3} label="Review" value={job.pending_review_count ?? 0} />
          <JobMetric icon={Cpu} label="Stages" value={job.stages.length} />
        </div>

        <div className="grid gap-2 sm:grid-cols-5">
          {pipelineSteps.map((step) => {
            const done = isPipelineStepDone(job, step.key)

            return (
              <div
                key={step.key}
                className={cn(
                  'flex min-h-10 items-center gap-2 rounded-md border px-2 text-xs',
                  done
                    ? 'border-primary/25 bg-primary/5 text-foreground'
                    : 'border-border bg-muted/30 text-muted-foreground',
                )}
              >
                {done ? (
                  <CheckCircle2 className="size-3.5 shrink-0" aria-hidden="true" />
                ) : (
                  <Circle className="size-3.5 shrink-0" aria-hidden="true" />
                )}
                <span className="truncate">{step.label}</span>
              </div>
            )
          })}
        </div>

        {job.warning ? (
          <p className="rounded-md border border-dashed px-3 py-2 text-xs leading-5 text-muted-foreground">
            {job.warning}
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
    <div className="flex min-w-0 items-center gap-2 rounded-md border bg-muted/30 px-3 py-2">
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium">{value}</p>
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
