import {
  CalendarClock,
  Database,
  FileText,
  GitBranch,
  Sparkles,
  Binary,
  type LucideIcon,
} from 'lucide-react'
import { useState, useMemo } from 'react'

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
import { getJobPhase, getStagePhase } from '@/features/jobs/job-progress'
import { cn } from '@/lib/utils'
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
  const stage = job ? getJobPhase(job) : 'indexed'
  const chunkCount = job?.chunk_count
  const candidateCount = job?.candidate_count

  // Generate highly premium stage colors compatible with Streamlit signatures
  const stageBadgeStyles = useMemo(() => {
    switch (stage.toLowerCase()) {
      case 'completed':
      case 'indexed':
        return 'bg-chart-3/10 text-chart-3 border-chart-3/20'
      case 'uploaded_to_database':
        return 'bg-primary/10 text-primary border-primary/20'
      case 'failed':
        return 'bg-destructive/10 text-destructive border-destructive/20'
      default:
        return 'bg-chart-2/10 text-chart-2 border-chart-2/20'
    }
  }, [stage])

  return (
    <>
      <Card
        role="button"
        tabIndex={0}
        className="cursor-pointer border border-border/80 bg-card/65 backdrop-blur-md rounded-2xl transition-all duration-300 hover:border-primary/25 hover:shadow-[0_8px_30px_oklch(var(--color-primary)/8%)] hover:-translate-y-1 group focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:outline-none overflow-hidden relative flex flex-col justify-between"
        onClick={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            setOpen(true)
          }
        }}
      >
        {/* Sleek top neon indicator border matching Streamlit theme */}
        <div className="absolute top-0 left-0 h-[3px] w-full bg-gradient-to-r from-primary via-chart-2 to-primary opacity-40 group-hover:opacity-100 transition-opacity duration-300" />

        <div className="flex-1">
          <CardHeader className="p-5 pb-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <CardTitle className="truncate text-sm font-extrabold tracking-tight group-hover:text-primary transition-colors duration-300 leading-snug">
                  {document.source_title}
                </CardTitle>
                <p className="mt-1 text-[9px] text-muted-foreground/60 font-black uppercase tracking-widest leading-none">
                  {document.file_name} • {document.file_type.toUpperCase()}
                </p>
              </div>
              <Badge variant="secondary" className={cn("font-black px-2 py-0.5 rounded-md text-[8px] uppercase tracking-wider border shrink-0", stageBadgeStyles)}>
                {stage === 'indexed' ? 'Indexed' : formatStage(stage)}
              </Badge>
            </div>
          </CardHeader>

          <CardContent className="grid gap-3.5 p-5 pt-0">
            {/* Ultra-Slim Technical Spec Grid - No thick borders or bulky blocks */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 bg-muted/10 border border-border/50 rounded-xl p-3 select-none">
              <DocumentMiniMeta icon={CalendarClock} label="Run Date" value={displayDate} />
              <DocumentMiniMeta icon={Database} label="System Stage" value={formatStage(stage)} />
              <DocumentMiniMeta icon={GitBranch} label="Ingest Job" value={job?.job_id ?? document.job_id ?? 'No Job ID'} />
              <DocumentMiniMeta 
                icon={FileText} 
                label="Staged Chunks" 
                value={chunkCount === undefined ? 'Unknown' : `${chunkCount} chunks`} 
              />
            </div>
          </CardContent>
        </div>

        {/* Card Footer - Redesigned for maximum premium visual cleaness */}
        <CardFooter className="justify-between gap-3 p-5 pt-1 border-t border-border/20 bg-muted/5 group-hover:bg-muted/15 transition-colors duration-300 shrink-0">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5">
            {candidateCount !== undefined ? (
              <span className="inline-flex items-center gap-1 text-[8.5px] font-black tracking-wider uppercase border border-chart-2/20 bg-chart-2/5 text-chart-2 px-2.5 py-0.5 rounded-md leading-none shadow-sm shadow-chart-2/2">
                {candidateCount} candidates
              </span>
            ) : null}
            {document.document_id ? (
              <span className="max-w-[8rem] truncate font-mono text-[8px] font-bold bg-background/55 tracking-wider px-2 py-0.5 rounded-md border border-border text-muted-foreground/80 leading-none">
                DOC: {document.document_id}
              </span>
            ) : null}
          </div>
          
          {/* Subtle micro arrow sparkles card entrance chip */}
          <div className="flex size-7 items-center justify-center rounded-lg bg-card border border-border group-hover:border-primary/20 group-hover:scale-105 group-hover:shadow-[0_0_12px_oklch(var(--color-primary)/10%)] transition-all duration-300 text-muted-foreground group-hover:text-primary">
            <Sparkles className="size-3.5 animate-pulse" />
          </div>
        </CardFooter>
      </Card>

      {/* Advanced high-performance Code/Document Studio Viewer modal */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-4xl max-h-[85vh] flex flex-col border border-primary/10 shadow-2xl rounded-2xl bg-card/95 backdrop-blur-md overflow-hidden p-0 animate-scale-up">
          <DialogHeader className="p-6 pb-4.5 bg-muted/15 border-b border-border/45 flex flex-row items-center gap-3 shrink-0">
            <div className="flex size-9.5 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 text-primary shadow-sm shadow-primary/2">
              <Binary className="size-5" />
            </div>
            <div className="min-w-0 flex-1">
              <DialogTitle className="text-base font-extrabold tracking-tight text-foreground truncate max-w-[28rem]">
                {document.source_title}
              </DialogTitle>
              <DialogDescription className="text-[10px] font-semibold text-muted-foreground/80 mt-1">
                File: {document.file_name} • Format: {document.file_type.toUpperCase()}
              </DialogDescription>
            </div>
          </DialogHeader>

          <div className="flex-1 min-h-0 overflow-y-auto p-6.5 space-y-5">
            {/* Quick Header Spec Info */}
            <div className="grid gap-3.5 sm:grid-cols-3 select-none">
              <DocumentDetailMeta icon={CalendarClock} label="Index Run Date" value={displayDate} />
              <DocumentDetailMeta icon={Database} label="System Stage Level" value={formatStage(stage)} />
              <DocumentDetailMeta icon={GitBranch} label="Graph Ingest Job ID" value={job?.job_id ?? document.job_id ?? 'No Job ID'} />
            </div>

            {/* Ingestion Pipeline Step Timeline Tracker */}
            {job && job.stages && job.stages.length > 0 ? (
              <div className="flex flex-col gap-2 bg-muted/10 border border-border/50 rounded-xl p-4.5 select-none">
                <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1">
                  Ingestion Pipeline Progress Steps
                </p>
                <div className="mt-2.5 space-y-3.5 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-border/60">
                  {job.stages.map((stg, idx) => {
                    const isSuccess = stg.status === 'success';
                    const isFailed = stg.status === 'failed';
                    return (
                      <div key={idx} className="flex items-start gap-3.5 relative pl-1">
                        <div className={cn(
                          "flex size-7 items-center justify-center rounded-lg border font-black text-[9px] z-10 bg-card shadow-sm",
                          isSuccess 
                            ? "text-chart-3 border-chart-3/30 bg-chart-3/5" 
                            : isFailed 
                              ? "text-destructive border-destructive/30 bg-destructive/5" 
                              : "text-primary border-primary/30 bg-primary/5 animate-pulse"
                        )}>
                          {idx + 1}
                        </div>
                        <div className="min-w-0 flex-1 mt-0.5">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-extrabold text-foreground uppercase tracking-wider leading-none">
                              {formatStage(getStagePhase(stg))}
                            </span>
                            <span className={cn(
                              "text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full border leading-none",
                              isSuccess 
                                ? "bg-chart-3/10 text-chart-3 border-chart-3/20" 
                                : isFailed 
                                  ? "bg-destructive/10 text-destructive border-destructive/20" 
                                  : "bg-primary/10 text-primary border-primary/20 animate-pulse"
                            )}>
                              {stg.status}
                            </span>
                          </div>
                          <p className="mt-1 text-[10px] text-muted-foreground font-semibold leading-relaxed">
                            {stg.message}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-2 bg-muted/10 border border-border/50 rounded-xl p-4.5 select-none">
                <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1">
                  Ingestion Pipeline Progress Steps
                </p>
                <div className="mt-2.5 space-y-3.5 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-border/60">
                  <div className="flex items-start gap-3.5 relative pl-1">
                    <div className="flex size-7 items-center justify-center rounded-lg border font-black text-[9px] z-10 bg-card shadow-sm text-chart-3 border-chart-3/30 bg-chart-3/5">
                      1
                    </div>
                    <div className="min-w-0 flex-1 mt-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-extrabold text-foreground uppercase tracking-wider leading-none">
                          Uploaded to Database
                        </span>
                        <span className="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full border leading-none bg-chart-3/10 text-chart-3 border-chart-3/20">
                          success
                        </span>
                      </div>
                      <p className="mt-1 text-[10px] text-muted-foreground font-semibold leading-relaxed">
                        Document raw text successfully indexed and stored in GraphRAG core database.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div className="flex flex-col gap-2">
              <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none pl-1">
                Raw Document Text Context
              </p>
              <ScrollArea className="h-[min(38vh,24rem)] rounded-xl border border-primary/10 bg-muted/20 p-5 focus-within:ring-1 focus-within:ring-primary/45 transition-all">
                <pre className="whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed text-foreground/90 select-text tracking-tight">
                  {document.content}
                </pre>
              </ScrollArea>
            </div>
          </div>
          
          <div className="p-4 px-6.5 bg-muted/15 border-t border-border/45 flex justify-end shrink-0 select-none">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-xs font-bold px-5 h-8.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/95 shadow-sm transition-all cursor-pointer"
            >
              Close Studio View
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function DocumentMiniMeta({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon
  label: string
  value: string
}) {
  return (
    <div className="flex min-w-0 items-start gap-1.5">
      <Icon className="size-3.5 shrink-0 text-muted-foreground/60 mt-0.5" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="text-[8px] font-black text-muted-foreground/45 uppercase tracking-widest leading-none">
          {label}
        </p>
        <p className="truncate text-[10px] font-bold text-foreground/80 mt-1 leading-none" title={value}>
          {value}
        </p>
      </div>
    </div>
  )
}

function DocumentDetailMeta({
  icon: Icon,
  label,
  value,
}: {
  icon: LucideIcon
  label: string
  value: string
}) {
  return (
    <div className="flex min-w-0 items-center gap-3 rounded-xl border border-border/60 bg-muted/40 px-3.5 py-2.5 transition-all duration-300 hover:bg-primary/5 hover:border-primary/15 group/meta">
      <div className="p-1 rounded-lg bg-card text-muted-foreground group-hover/meta:text-primary transition-colors duration-300">
        <Icon className="size-4 shrink-0" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest leading-none">
          {label}
        </p>
        <p className="truncate text-xs font-bold text-foreground/90 mt-1 leading-none">{value}</p>
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
