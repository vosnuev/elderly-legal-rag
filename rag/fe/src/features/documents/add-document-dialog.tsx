import { useState } from 'react'
import { Upload } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

type AddDocumentDialogProps = {
  onOpenChange: (open: boolean) => void
  onSubmit: (fileName: string, content: string) => void
  open: boolean
}

export function AddDocumentDialog({
  onOpenChange,
  onSubmit,
  open,
}: AddDocumentDialogProps) {
  const [fileName, setFileName] = useState('')
  const [content, setContent] = useState('')
  const [dragging, setDragging] = useState(false)

  async function readFile(file: File) {
    const text = await file.text()
    setFileName(file.name)
    setContent(text)
  }

  function submit() {
    const trimmedFileName = fileName.trim()
    const trimmedContent = content.trim()

    if (!trimmedFileName || !trimmedContent) {
      return
    }

    onSubmit(trimmedFileName, trimmedContent)
    setFileName('')
    setContent('')
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Add Document</DialogTitle>
          <DialogDescription>
            Upload or paste a text, JSON, Markdown, or CSV document for the RAG ingest flow.
          </DialogDescription>
        </DialogHeader>

        <label
          className={cn(
            'flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed px-4 text-center',
            dragging ? 'border-primary bg-muted' : 'border-border bg-muted/40',
          )}
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            const file = event.dataTransfer.files.item(0)
            if (file) {
              void readFile(file)
            }
          }}
        >
          <Upload className="size-7 text-muted-foreground" aria-hidden="true" />
          <span className="mt-3 text-sm font-medium">Drop text document</span>
          <input
            name="document-file"
            type="file"
            accept=".txt,.md,.json,.csv"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.item(0)
              if (file) {
                void readFile(file)
              }
            }}
          />
        </label>

        <div className="grid gap-3">
          <Input
            name="document-file-name"
            value={fileName}
            onChange={(event) => setFileName(event.target.value)}
            placeholder="document.json"
          />
          <Textarea
            name="document-content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            className="min-h-72 font-mono leading-6 lg:min-h-80"
            placeholder="Paste text, JSON, Markdown, or CSV"
          />
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="button" disabled={!fileName.trim() || !content.trim()} onClick={submit}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
