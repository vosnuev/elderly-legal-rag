import { useMemo, useState } from 'react'
import {
  AlertCircle,
  BookOpenText,
  Check,
  Clock3,
  FilePlus2,
  GitBranch,
  Loader2,
  Upload,
} from 'lucide-react'

import { MetricCard } from '@/components/workspace/metric-card'
import { PageHeader } from '@/components/workspace/page-header'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { AddDocumentDialog } from '@/features/documents/add-document-dialog'
import { DocumentCard } from '@/features/documents/document-card'
import { DocumentSearch } from '@/features/documents/document-search'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'

export function DocumentsPage() {
  const {
    documents,
    jobs,
    pendingReviewCount,
    stageDocument,
    status,
  } = useRagWorkspace()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [query, setQuery] = useState('')

  const filteredDocuments = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      return documents
    }

    return documents.filter((document) =>
      `${document.source_title} ${document.file_name} ${document.content}`
        .toLowerCase()
        .includes(normalized),
    )
  }, [documents, query])

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        title="Documents"
        description="Stored RAG documents and ingest status."
        action={
          <Button type="button" onClick={() => setDialogOpen(true)}>
            <FilePlus2 data-icon="inline-start" aria-hidden="true" />
            Add Document
          </Button>
        }
      />

      <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
        <MetricCard label="Documents" value={documents.length} icon={<BookOpenText className="size-4" />} />
        <MetricCard label="Jobs" value={jobs.length} icon={<GitBranch className="size-4" />} />
        <MetricCard label="Pending" value={pendingReviewCount} icon={<Clock3 className="size-4" />} />
        <MetricCard
          label="Backend"
          value={status === 'loading' ? 'Sync' : status === 'error' ? 'Down' : 'Ready'}
          icon={
            status === 'loading' ? (
              <Loader2 className="size-4 animate-spin" />
            ) : status === 'error' ? (
              <AlertCircle className="size-4" />
            ) : (
              <Check className="size-4" />
            )
          }
        />
      </div>

      <DocumentSearch value={query} onChange={setQuery} />

      <div className="grid gap-3">
        {filteredDocuments.length === 0 ? (
          <Card>
            <CardContent className="flex min-h-64 items-center justify-center">
              <div className="text-center">
                <Upload className="mx-auto size-7 text-muted-foreground" aria-hidden="true" />
                <p className="mt-3 text-sm font-medium">No indexed documents</p>
              </div>
            </CardContent>
          </Card>
        ) : (
          filteredDocuments.map((document) => (
            <DocumentCard
              key={`${document.file_name}-${document.location ?? 'root'}`}
              document={document}
            />
          ))
        )}
      </div>

      <AddDocumentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmit={(fileName, content) => {
          void stageDocument(fileName, content)
          setDialogOpen(false)
        }}
      />
    </div>
  )
}
