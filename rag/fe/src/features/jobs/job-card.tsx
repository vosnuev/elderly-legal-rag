import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import type { FileIngestStatusResponse } from '@/types'

type JobCardProps = {
  job: FileIngestStatusResponse
}

export function JobCard({ job }: JobCardProps) {
  return (
    <Card size="sm">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="truncate">{job.file_name}</CardTitle>
          <Badge variant={job.completed ? 'secondary' : 'outline'}>
            {job.completed ? 'Done' : 'Open'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{job.current_stage}</p>
      </CardContent>
    </Card>
  )
}
