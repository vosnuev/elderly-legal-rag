import { useState, useRef } from 'react'
import {
  Upload,
  CheckCircle2,
  AlertCircle,
  FileJson,
  FileSpreadsheet,
  FileText,
  Sparkles,
  FileUp,
  FileSignature
} from 'lucide-react'

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

type FileMetadata = {
  sizeBytes: number
  sizeKB: string
  lines: number
  words: number
  type: string
  isValid: boolean
  error?: string
}

const SUPPORTED_UPLOAD_EXTENSIONS = ['.txt', '.md', '.json', '.csv', '.toon'] as const

export function AddDocumentDialog({
  onOpenChange,
  onSubmit,
  open,
}: AddDocumentDialogProps) {
  const [activeTab, setActiveTab] = useState<'upload' | 'paste'>('upload')
  const [fileName, setFileName] = useState('')
  const [content, setContent] = useState('')
  const [dragging, setDragging] = useState(false)
  const [fileMeta, setFileMeta] = useState<FileMetadata | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleFileRead(file: File) {
    try {
      const text = await file.text()
      
      // Calculate basic analytics
      const bytes = file.size
      const kb = (bytes / 1024).toFixed(2)
      const lines = text.split(/\r?\n/).length
      const words = text.trim() === '' ? 0 : text.trim().split(/\s+/).length
      const extension = file.name.split('.').pop()?.toLowerCase() || ''
      
      let isValid = true
      let errorMsg: string | undefined

      // Client-side Format Validation check
      if (extension === 'json') {
        try {
          JSON.parse(text)
        } catch (error: unknown) {
          isValid = false
          errorMsg = `Invalid JSON: ${getErrorMessage(error) || 'Syntax error'}`
        }
      } else if (extension === 'csv') {
        // Simple CSV validation: check if rows have similar column counts roughly
        const rows = text.trim().split('\n')
        if (rows.length > 0) {
          const colCount = rows[0].split(',').length
          if (colCount <= 1 && text.includes(';')) {
            // Might be semi-colon separated, check
            const semiColCount = rows[0].split(';').length
            if (semiColCount > 1) {
              // Valid semi-colon CSV
            } else {
              isValid = false
              errorMsg = 'CSV format seems suspicious (only 1 column found)'
            }
          }
        }
      }

      setFileName(file.name)
      setContent(text)
      setFileMeta({
        sizeBytes: bytes,
        sizeKB: kb,
        lines,
        words,
        type: file.type || extension,
        isValid,
        error: errorMsg,
      })
      setParseError(errorMsg || null)
    } catch (error: unknown) {
      setParseError(`Failed to read file: ${getErrorMessage(error)}`)
    }
  }

  function handleReset() {
    setFileName('')
    setContent('')
    setFileMeta(null)
    setParseError(null)
  }

  function submit() {
    const trimmedFileName = fileName.trim()
    const trimmedContent = content.trim()

    if (!trimmedFileName || !trimmedContent || (fileMeta && !fileMeta.isValid)) {
      return
    }

    onSubmit(trimmedFileName, trimmedContent)
    handleReset()
  }

  const getFormatBadge = (name: string, meta: FileMetadata | null) => {
    if (!meta) return null
    const ext = name.split('.').pop()?.toLowerCase()
    
    if (meta.error) {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-destructive/10 text-destructive border border-destructive/20 animate-shake">
          <AlertCircle className="size-3" />
          {meta.error}
        </span>
      )
    }

    if (ext === 'json') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-chart-2/15 text-chart-2 border border-chart-2/30">
          <FileJson className="size-3 animate-pulse" />
          Valid JSON
        </span>
      )
    }
    if (ext === 'csv') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-primary/15 text-primary border border-primary/30">
          <FileSpreadsheet className="size-3" />
          Valid CSV
        </span>
      )
    }
    if (ext === 'toon') {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-chart-3/15 text-chart-3 border border-chart-3/30">
          <FileText className="size-3" />
          TOON Text
        </span>
      )
    }
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-muted-foreground/10 text-muted-foreground border border-muted-foreground/20">
        <FileText className="size-3" />
        Raw Text/Markdown
      </span>
    )
  }

  return (
    <Dialog open={open} onOpenChange={(val) => {
      onOpenChange(val)
      if (!val) handleReset()
    }}>
      <DialogContent className="sm:max-w-4xl border border-primary/10 shadow-2xl dark:shadow-primary/5 rounded-2xl overflow-hidden bg-card/95 backdrop-blur-md p-0 flex flex-col max-h-[88vh]">
        
        <DialogHeader className="p-6 pb-4.5 bg-muted/15 border-b border-border/45 flex flex-row items-center gap-3 shrink-0">
          <div className="flex size-9.5 items-center justify-center rounded-xl bg-gradient-to-tr from-primary to-chart-2 text-primary-foreground font-black text-xs shadow-md">
            <Sparkles className="size-5 animate-pulse" />
          </div>
          <div>
            <DialogTitle className="text-base font-extrabold tracking-tight bg-gradient-to-r from-primary via-chart-2 to-primary bg-clip-text text-transparent">
              Ingest Workspace Document
            </DialogTitle>
            <DialogDescription className="text-[10px] font-semibold text-muted-foreground/80 mt-1">
              Ingest unstructured records into GraphRAG core workspace. Drag & Drop physical files or paste manual content.
            </DialogDescription>
          </div>
        </DialogHeader>

        <div className="p-6.5 space-y-5 flex-1 min-h-0 overflow-y-auto">
          {/* Custom Premium Tabs Component */}
          <div className="flex p-1 rounded-xl bg-muted/40 border border-border/40 gap-1 select-none">
            <button
              type="button"
              onClick={() => {
                setActiveTab('upload')
                handleReset()
              }}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-extrabold transition-all duration-300 cursor-pointer",
                activeTab === 'upload'
                  ? "bg-card text-primary border border-primary/15 shadow-sm scale-[1.01]"
                  : "text-muted-foreground hover:bg-muted/30 hover:text-foreground"
              )}
            >
              <FileUp className="size-3.5" />
              <span>Upload Local File</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('paste')
                handleReset()
              }}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-extrabold transition-all duration-300 cursor-pointer",
                activeTab === 'paste'
                  ? "bg-card text-primary border border-primary/15 shadow-sm scale-[1.01]"
                  : "text-muted-foreground hover:bg-muted/30 hover:text-foreground"
              )}
            >
              <FileSignature className="size-3.5" />
              <span>Direct Paste Input</span>
            </button>
          </div>

          {/* Tab Content Panel */}
          <div className="space-y-4">
            {activeTab === 'upload' ? (
              <div className="grid gap-4">
                {/* Interactive Drag & Drop Sandbox Zone */}
                <label
                  className={cn(
                    'flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed text-center transition-all duration-300 p-6 relative overflow-hidden group',
                    dragging
                      ? 'border-primary bg-primary/8 shadow-[inset_0_0_15px_oklch(var(--color-primary)/10%)] scale-[0.995]'
                      : fileName 
                        ? 'border-chart-2/45 bg-chart-2/4 hover:bg-chart-2/6 shadow-inner'
                        : 'border-border bg-muted/20 hover:border-primary/30 hover:bg-muted/30'
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
                      void handleFileRead(file)
                    }
                  }}
                >
                  {/* Floating Neumorphic Decorative Auras */}
                  <div className="absolute -top-12 -left-12 size-24 rounded-full bg-primary/5 blur-xl group-hover:bg-primary/8 transition-colors pointer-events-none" />
                  <div className="absolute -bottom-12 -right-12 size-24 rounded-full bg-chart-2/5 blur-xl group-hover:bg-chart-2/8 transition-colors pointer-events-none" />

                  {fileName ? (
                    <div className="flex flex-col items-center gap-2 animate-bounce-short">
                      <div className="flex size-12 items-center justify-center rounded-full bg-chart-2/15 border border-chart-2/30 text-chart-2 shadow-sm">
                        <CheckCircle2 className="size-6 animate-pulse" />
                      </div>
                      <span className="text-sm font-extrabold tracking-tight text-foreground/90 mt-1">
                        File Loaded Successfully!
                      </span>
                      <span className="text-[11px] font-bold text-muted-foreground max-w-[20rem] truncate">
                        {fileName}
                      </span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <div className="flex size-11 items-center justify-center rounded-xl bg-card border border-border group-hover:border-primary/20 shadow-sm group-hover:scale-105 group-hover:shadow-[0_0_15px_oklch(var(--color-primary)/10%)] transition-all duration-300 text-muted-foreground group-hover:text-primary">
                        <Upload className="size-5" />
                      </div>
                      <span className="mt-3 text-xs font-bold text-foreground">
                        Drag and drop local data file here
                      </span>
                      <span className="mt-1 text-[10px] text-muted-foreground/80 font-medium max-w-[20rem]">
                        Supports <span className="font-mono text-primary/80">{SUPPORTED_UPLOAD_EXTENSIONS.join(', ')}</span> formats
                      </span>
                      <span className="mt-4 inline-flex items-center gap-1.5 px-3 py-1 rounded-full border bg-card text-[9px] font-bold text-muted-foreground group-hover:text-foreground group-hover:border-border transition-colors">
                        Or browse local files
                      </span>
                    </div>
                  )}

                  <input
                    ref={fileInputRef}
                    name="document-file"
                    type="file"
                    accept={SUPPORTED_UPLOAD_EXTENSIONS.join(',')}
                    className="sr-only"
                    onChange={(event) => {
                      const file = event.target.files?.item(0)
                      if (file) {
                        void handleFileRead(file)
                      }
                    }}
                  />
                </label>

                {/* File Meta Summary & Verification Panel */}
                {fileMeta && (
                  <div className="grid gap-3.5 border border-border/80 rounded-xl bg-card/60 p-4 shadow-sm relative overflow-hidden animate-fade-in">
                    <div className="absolute top-0 left-0 h-0.5 w-full bg-gradient-to-r from-primary to-chart-2" />
                    
                    <div className="flex flex-wrap items-center justify-between gap-3 select-none">
                      <span className="text-[10px] font-black text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                        <Sparkles className="size-3.5 text-primary" />
                        Ingest Content Diagnostics
                      </span>
                      {getFormatBadge(fileName, fileMeta)}
                    </div>

                    {/* Realtime Analyzer Metrics */}
                    <div className="grid grid-cols-4 gap-2 text-center select-none">
                      <div className="bg-muted/30 border border-border/40 rounded-lg p-2 flex flex-col justify-center">
                        <span className="text-[10px] font-bold text-muted-foreground">File Name</span>
                        <span className="text-[11px] font-extrabold text-foreground truncate mt-0.5 max-w-[8rem]" title={fileName}>
                          {fileName}
                        </span>
                      </div>
                      <div className="bg-muted/30 border border-border/40 rounded-lg p-2 flex flex-col justify-center">
                        <span className="text-[10px] font-bold text-muted-foreground">Volume Size</span>
                        <span className="text-[11px] font-extrabold text-foreground mt-0.5 font-mono">
                          {fileMeta.sizeKB} KB
                        </span>
                      </div>
                      <div className="bg-muted/30 border border-border/40 rounded-lg p-2 flex flex-col justify-center">
                        <span className="text-[10px] font-bold text-muted-foreground">Total Lines</span>
                        <span className="text-[11px] font-extrabold text-foreground mt-0.5 font-mono">
                          {fileMeta.lines}
                        </span>
                      </div>
                      <div className="bg-muted/30 border border-border/40 rounded-lg p-2 flex flex-col justify-center">
                        <span className="text-[10px] font-bold text-muted-foreground">Word Count</span>
                        <span className="text-[11px] font-extrabold text-foreground mt-0.5 font-mono">
                          {fileMeta.words}
                        </span>
                      </div>
                    </div>

                    {/* Collapsible raw content viewport preview */}
                    <div className="mt-1 border border-border/50 rounded-lg overflow-hidden">
                      <div className="bg-muted/20 border-b border-border/50 px-3 py-1.5 flex items-center justify-between select-none">
                        <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-none">
                          Parsed File Contents Preview
                        </span>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-4.5 px-1.5 text-[9px] font-extrabold text-primary hover:bg-primary/5 shrink-0 cursor-pointer"
                          onClick={handleReset}
                        >
                          Reset File
                        </Button>
                      </div>
                      <div className="max-h-36 overflow-y-auto p-3 font-mono text-[10px] leading-relaxed bg-muted/10 text-foreground/90 whitespace-pre-wrap select-text">
                        {content.slice(0, 1000)}
                        {content.length > 1000 ? '\n\n... (Truncated for preview length)' : ''}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="grid gap-3.5 animate-fade-in">
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-black text-muted-foreground uppercase tracking-wider">
                    Target File Name
                  </label>
                  <Input
                    name="document-file-name"
                    value={fileName}
                    onChange={(event) => setFileName(event.target.value)}
                    placeholder="e.g. core-features.md"
                    className="h-9 text-xs rounded-lg border-border focus-visible:ring-primary focus-visible:border-primary placeholder:text-muted-foreground/60 font-semibold"
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] font-black text-muted-foreground uppercase tracking-wider">
                    Document Body Raw Content
                  </label>
                  <Textarea
                    name="document-content"
                    value={content}
                    onChange={(event) => setContent(event.target.value)}
                    className="min-h-56 font-mono text-[11px] leading-relaxed p-3.5 rounded-lg border-border focus-visible:ring-primary focus-visible:border-primary placeholder:text-muted-foreground/50 select-text"
                    placeholder="Paste manual Markdown, CSV rows, or JSON string directly into this console..."
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="p-4 px-6.5 bg-muted/15 border-t border-border/45 flex items-center justify-between gap-3 shrink-0 select-none">
          <div className="flex-1 text-[10px] text-muted-foreground/75 font-semibold leading-normal max-sm:hidden">
            {fileName && content && !parseError ? (
              <span className="text-chart-2 font-bold flex items-center gap-1">
                <CheckCircle2 className="size-3.5 shrink-0 animate-pulse" />
                Diagnostics Passed. Ready to ingest into GraphRAG.
              </span>
            ) : parseError ? (
              <span className="text-destructive font-bold flex items-center gap-1">
                <AlertCircle className="size-3.5 shrink-0 animate-bounce-short" />
                Validations failed: Resolve parser error before saving.
              </span>
            ) : (
              "Complete all required configurations to unlock database ingestion."
            )}
          </div>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="text-xs font-bold px-4 h-9 rounded-lg hover:bg-muted cursor-pointer"
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={!fileName.trim() || !content.trim() || !!parseError}
              onClick={submit}
              className="text-xs font-extrabold px-5.5 h-9 rounded-lg bg-gradient-to-r from-primary to-primary hover:from-primary/95 hover:to-primary/95 text-primary-foreground shadow-sm shadow-primary/10 cursor-pointer"
            >
              Save & Ingest
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}
