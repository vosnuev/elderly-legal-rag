import {
  CalendarClock,
  Database,
  FileText,
  GitBranch,
  type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardFooter,
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
import { ScrollArea } from '@/components/ui/scroll-area'
import type {
  FileIngestStatusResponse,
  RagDocument,
} from '@/types'

type DocumentCardProps = {
  document: RagDocument
  job?: FileIngestStatusResponse
}

export function DocumentCard({ document, job }: DocumentCardProps) {
  const [open, setOpen] = useState(false)
  const runDate = getDocumentRunDate(document, job)
  const displayDate = formatDateTime(runDate)
  const stage = job?.current_stage ?? 'indexed'
  const chunkCount = job?.chunk_count
  const candidateCount = job?.candidate_count

  return (
    <>
      <Card
        role="button"
        tabIndex={0}
        className="cursor-pointer transition-colors hover:bg-muted/30 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
        onClick={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            setOpen(true)
          }
        }}
      >
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <CardTitle className="truncate">{document.source_title}</CardTitle>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {document.file_name} · {document.file_type}
              </p>
            </div>
            <Badge variant="secondary">Indexed</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4">
          <p className="line-clamp-4 text-sm leading-6 text-muted-foreground">
            {document.content}
          </p>

          <div className="grid gap-2 sm:grid-cols-2">
            <DocumentMeta icon={CalendarClock} label="Run date" value={displayDate} />
            <DocumentMeta icon={Database} label="Stage" value={formatStage(stage)} />
            <DocumentMeta icon={GitBranch} label="Job" value={job?.job_id ?? document.job_id ?? 'No job'} />
            <DocumentMeta
              icon={FileText}
              label="Chunks"
              value={chunkCount === undefined ? 'Unknown' : String(chunkCount)}
            />
          </div>
        </CardContent>
        <CardFooter className="justify-between gap-2">
          <div className="flex min-w-0 flex-wrap gap-2">
            {candidateCount !== undefined ? (
              <Badge variant="outline">{candidateCount} candidates</Badge>
            ) : null}
            {document.document_id ? (
              <Badge variant="outline" className="max-w-44 justify-start truncate">
                {document.document_id}
              </Badge>
            ) : null}
          </div>
          <span className="inline-flex h-7 shrink-0 items-center justify-center rounded-md border bg-background px-2.5 text-[0.8rem] font-medium">
            Open source
          </span>
        </CardFooter>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>{document.source_title}</DialogTitle>
            <DialogDescription>
              {document.file_name} · {document.file_type} · Run date {displayDate}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3">
            <div className="grid gap-2 sm:grid-cols-3">
              <DocumentMeta icon={CalendarClock} label="Run date" value={displayDate} />
              <DocumentMeta icon={Database} label="Stage" value={formatStage(stage)} />
              <DocumentMeta icon={GitBranch} label="Job" value={job?.job_id ?? document.job_id ?? 'No job'} />
            </div>
            <ScrollArea className="h-[min(62vh,42rem)] rounded-md border bg-background">
              <pre className="whitespace-pre-wrap break-words p-4 font-mono text-sm leading-6">
                {document.content}
              </pre>
            </ScrollArea>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function DocumentMeta({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon
  label: string
  value: string
}) {
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-md border bg-background px-3 py-2">
      <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="truncate text-sm font-medium">{value}</p>
      </div>
    </div>
  )
}

function getDocumentRunDate(document: RagDocument, job?: FileIngestStatusResponse) {
  return (
    document.indexed_at ??
    document.updated_at ??
    document.created_at ??
    job?.completed_at ??
    job?.updated_at ??
    job?.created_at ??
    null
  )
}

function formatDateTime(value: string | null) {
  if (!value) {
    return 'Unknown'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('ko-KR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function formatStage(stage: string) {
  return stage.replaceAll('_', ' ')
}
