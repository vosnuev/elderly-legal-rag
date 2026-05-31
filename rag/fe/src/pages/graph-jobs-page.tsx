import { GitBranch, Play } from 'lucide-react'

import { JobCard } from '@/features/jobs/job-card'
import { PageHeader } from '@/components/workspace/page-header'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'

export function GraphJobsPage() {
  const { jobs, latestJob, startGraphAddForJob, status } = useRagWorkspace()

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Graph Jobs"
        description="Start graph-add processing from the latest staged document and review recent ingest jobs."
      />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <CardTitle>Graph Add</CardTitle>
              <CardDescription>Run graph expansion for the latest job.</CardDescription>
            </div>
            <GitBranch className="size-5 text-muted-foreground" aria-hidden="true" />
          </div>
        </CardHeader>
        <CardContent>
          {latestJob ? (
            <div className="grid gap-3 rounded-md border p-3">
              <div>
                <p className="truncate text-sm font-medium">{latestJob.file_name}</p>
                <p className="mt-1 text-xs text-muted-foreground">{latestJob.current_stage}</p>
              </div>
              <Button
                type="button"
                onClick={() => void startGraphAddForJob(latestJob.job_id)}
                disabled={status === 'loading'}
              >
                <Play data-icon="inline-start" aria-hidden="true" />
                Start Graph Add
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No jobs are available.</p>
          )}
        </CardContent>
      </Card>

      <section className="grid gap-3">
        <h3 className="text-sm font-semibold">Recent Jobs</h3>
        {jobs.map((job) => (
          <JobCard key={job.job_id} job={job} />
        ))}
      </section>
    </div>
  )
}
