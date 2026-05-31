import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import type { RagDocument } from '@/types'

type DocumentCardProps = {
  document: RagDocument
}

export function DocumentCard({ document }: DocumentCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="truncate">{document.source_title}</CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              {document.file_name} · {document.file_type}
              {document.location ? ` · ${document.location}` : ''}
            </p>
          </div>
          <Badge variant="secondary">Indexed</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
          {document.content}
        </p>
      </CardContent>
    </Card>
  )
}
