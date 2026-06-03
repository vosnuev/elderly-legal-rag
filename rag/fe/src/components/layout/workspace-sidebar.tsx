import {
  BookOpenText,
  Brain,
  CheckCircle2,
  Loader2,
  Settings,
} from 'lucide-react'
import { NavLink } from 'react-router'
import {
  useEffect,
  useRef,
  useState,
} from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
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
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'
import { cn } from '@/lib/utils'
import { navigationItems } from '@/routes/navigation'

const DEFAULT_MEMORY_TITLE = 'Candidate extraction memory'

export function WorkspaceSidebar() {
  const {
    memory,
    saveMemory,
    status,
  } = useRagWorkspace()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftContent, setDraftContent] = useState('')
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const resetSaveStateTimer = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (resetSaveStateTimer.current !== null) {
        window.clearTimeout(resetSaveStateTimer.current)
      }
    }
  }, [])

  const openMemorySettings = () => {
    setDraftTitle(memory?.title || DEFAULT_MEMORY_TITLE)
    setDraftContent(memory?.content || '')
    setSaveState('idle')
    setDialogOpen(true)
  }

  const saveDraft = async () => {
    setSaveState('saving')

    try {
      await saveMemory({
        content: draftContent,
        title: draftTitle.trim() || DEFAULT_MEMORY_TITLE,
        update_summary: 'FE Candidate extraction memory manual update',
      })
      setSaveState('saved')
      toast.success('Candidate memory saved', {
        description: 'Graph candidate extraction will use the updated memory.',
      })

      if (resetSaveStateTimer.current !== null) {
        window.clearTimeout(resetSaveStateTimer.current)
      }
      resetSaveStateTimer.current = window.setTimeout(() => {
        setDialogOpen(false)
        setSaveState('idle')
      }, 650)
    } catch {
      setSaveState('idle')
      toast.error('Memory save failed', {
        description: 'Check the RAG backend connection and try again.',
      })
    }
  }

  const canSave =
    draftTitle.trim().length > 0 &&
    draftContent.trim().length > 0 &&
    status !== 'loading' &&
    saveState === 'idle'
  const displayedMemoryTitle = memory?.title || DEFAULT_MEMORY_TITLE
  const saveButtonLabel =
    saveState === 'saving'
      ? 'Saving'
      : saveState === 'saved'
        ? 'Saved'
        : 'Save Memory'

  return (
    <aside className="flex h-full min-h-0 flex-col rounded-2xl border bg-card/45 backdrop-blur-xl p-5 shadow-xl shadow-primary/5 text-sidebar-foreground border-primary/10 max-lg:h-auto max-lg:w-full max-lg:p-4 transition-all duration-300">
      {/* Brand Logo Header */}
      <div className="flex items-center gap-3.5 select-none">
        <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-tr from-primary to-chart-2 text-primary-foreground shadow-lg shadow-primary/20 relative overflow-hidden group">
          <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
          <BookOpenText className="size-5.5 relative z-10" aria-hidden="true" />
        </div>
        <div>
          <p className="text-base font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/80">
            RAG Library
          </p>
          <p className="text-xs text-primary/70 font-semibold tracking-wider uppercase">
            GraphRAG Core
          </p>
        </div>
      </div>

      <nav className="mt-8 flex flex-col gap-1.5 max-lg:mt-4 max-lg:flex-row max-lg:overflow-x-auto select-none">
        {navigationItems.map(({ externalUrl, label, path, icon: Icon }) => {
          const itemClassName =
            'flex h-11 shrink-0 items-center gap-3.5 rounded-xl px-4 text-sm font-semibold transition-all duration-300 relative group overflow-hidden'

          if (externalUrl) {
            return (
              <a
                key={externalUrl}
                href={externalUrl}
                target="_blank"
                rel="noreferrer"
                className={cn(
                  itemClassName,
                  'text-muted-foreground hover:text-foreground hover:bg-primary/5 hover:translate-x-1 max-lg:hover:translate-x-0'
                )}
              >
                <Icon className="size-4.5 text-muted-foreground/80 group-hover:text-primary transition-colors" aria-hidden="true" />
                <span>{label}</span>
              </a>
            )
          }

          return (
            <NavLink
              key={path}
              to={path ?? '/'}
              end
              className={({ isActive }) =>
                cn(
                  itemClassName,
                  isActive
                    ? 'bg-gradient-to-r from-primary/15 to-chart-2/5 text-primary border-l-3 border-primary shadow-[0_4px_12px_oklch(var(--color-primary)/8%)]'
                    : 'text-muted-foreground hover:text-foreground hover:bg-primary/5 hover:translate-x-1 max-lg:hover:translate-x-0'
                )
              }
            >
              <Icon className="size-4.5 transition-colors duration-300" aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div className="mt-auto pt-5 max-lg:mt-4 max-lg:pt-0">
        <button
          type="button"
          onClick={openMemorySettings}
          className="group flex w-full items-center gap-3 rounded-xl border border-primary/10 bg-background/45 p-3 text-left transition-all duration-300 hover:border-primary/30 hover:bg-primary/5"
        >
          <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Brain className="size-4.5" aria-hidden="true" />
          </span>
          <span className="min-w-0 flex-1">
            <span className="block text-[8px] font-black uppercase tracking-widest text-muted-foreground">
              Candidate Memory
            </span>
            <span className="mt-0.5 flex items-center gap-1.5">
              <span className="truncate text-xs font-black text-foreground/90 transition-colors group-hover:text-primary">
                {displayedMemoryTitle}
              </span>
              <Badge
                variant="outline"
                className="h-3.5 shrink-0 rounded-md border-primary/10 bg-primary/5 px-1 text-[7.5px] font-black text-primary"
              >
                v{memory?.version ?? 0}
              </Badge>
            </span>
          </span>
          <Settings className="size-4 shrink-0 text-muted-foreground/50 transition-colors group-hover:text-primary" aria-hidden="true" />
        </button>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="flex max-h-[88vh] flex-col overflow-hidden rounded-2xl border border-primary/10 bg-card p-0 shadow-2xl sm:max-w-2xl">
          <DialogHeader className="shrink-0 border-b border-border/45 bg-muted/15 p-5">
            <div className="flex items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl border border-primary/15 bg-primary/10 text-primary">
                <Brain className="size-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <DialogTitle className="text-base font-extrabold text-foreground">
                  Candidate Extraction Memory
                </DialogTitle>
                <DialogDescription className="mt-1 text-xs font-semibold text-muted-foreground">
                  Relationship candidate를 뽑는 Graph Candidate Agent에 항상 주입되는 memory입니다.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
            <label className="flex flex-col gap-1.5">
              <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                Memory title
              </span>
              <Input
                value={draftTitle}
                onChange={(event) => setDraftTitle(event.target.value)}
                className="h-9 rounded-lg bg-background/50 text-sm font-bold"
                placeholder={DEFAULT_MEMORY_TITLE}
              />
            </label>

            <label className="flex min-h-0 flex-1 flex-col gap-1.5">
              <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                Memory markdown
              </span>
              <Textarea
                value={draftContent}
                onChange={(event) => setDraftContent(event.target.value)}
                className="min-h-[24rem] flex-1 resize-y rounded-xl bg-background/50 font-mono text-xs leading-relaxed"
                placeholder="후보 관계 생성 기준, 제외해야 할 관계 유형, reviewer note 반영 기준 등을 markdown으로 작성하세요."
              />
            </label>
          </div>

          <DialogFooter className="m-0 shrink-0 rounded-b-2xl border-t border-border/45 bg-muted/15 p-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setDialogOpen(false)}
              className="h-9 rounded-xl px-4 text-xs font-bold"
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={() => void saveDraft()}
              disabled={!canSave}
              className="h-9 min-w-28 rounded-xl px-5 text-xs font-extrabold"
            >
              {saveState === 'saving' && <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />}
              {saveState === 'saved' && <CheckCircle2 className="size-3.5" aria-hidden="true" />}
              {saveButtonLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  )
}
