import { RefreshCw } from 'lucide-react'
import { Outlet } from 'react-router'

import { WorkspaceSidebar } from '@/components/layout/workspace-sidebar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'

export function WorkspaceLayout() {
  const { message, refresh, status } = useRagWorkspace()
  const backendStatus = backendConnectionStatus(status, message)

  return (
    <main className="relative h-screen bg-background text-foreground overflow-hidden">
      {/* Futuristic Background Gradients (Atmospheric Glow) */}
      <div className="pointer-events-none absolute -top-[40%] -left-[20%] h-[80%] w-[60%] rounded-full bg-primary/10 blur-[120px] dark:bg-primary/5" />
      <div className="pointer-events-none absolute -bottom-[40%] -right-[10%] h-[80%] w-[60%] rounded-full bg-chart-2/10 blur-[120px] dark:bg-chart-2/5" />
      
      {/* Fine grid/dot pattern across the page */}
      <div className="pointer-events-none absolute inset-0 bg-grid-pattern opacity-[0.4] dark:opacity-[0.15]" />

      <div className="relative grid h-full min-h-0 grid-cols-[72px_minmax(0,1fr)] items-stretch gap-6 p-4 max-lg:grid-cols-1 max-lg:grid-rows-[auto_minmax(0,1fr)] max-lg:p-2">
        <WorkspaceSidebar />

        <section className="flex h-full min-h-0 flex-col min-w-0 rounded-2xl border bg-card/60 backdrop-blur-xl px-8 py-7 shadow-xl shadow-primary/5 max-sm:px-4">
          <header className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary via-primary to-chart-2">
                Document Workspace
              </h1>
              <p className="mt-1 text-sm text-muted-foreground font-medium">{message}</p>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              <div
                aria-label={`RAG backend ${backendStatus.label}`}
                className={`flex h-9 items-center gap-2 rounded-lg border px-3 text-[10px] font-black uppercase tracking-widest ${backendStatus.containerClass}`}
              >
                <span className={`size-2.5 rounded-full ${backendStatus.lightClass}`} />
                {backendStatus.label}
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => void refresh()}
                disabled={status === 'loading'}
                className="border-primary/20 hover:border-primary/50 transition-all duration-300 hover:shadow-[0_0_15px_oklch(var(--color-primary)/15%)]"
              >
                <RefreshCw
                  data-icon="inline-start"
                  className={status === 'loading' ? 'animate-spin text-primary' : 'text-primary'}
                  aria-hidden="true"
                />
                Sync Workspace
              </Button>
            </div>
          </header>

          <Separator className="my-6 bg-border/60" />

          <div className="flex-1 min-h-0 overflow-hidden">
            <Outlet />
          </div>
        </section>
      </div>
    </main>
  )
}

function backendConnectionStatus(status: string, message: string) {
  if (status === 'loading') {
    return {
      containerClass: 'border-amber-500/25 bg-amber-500/8 text-amber-600 dark:text-amber-400',
      label: 'Checking',
      lightClass: 'bg-amber-400 shadow-[0_0_10px_oklch(0.83_0.17_83/70%)] animate-pulse',
    }
  }

  const normalizedMessage = message.toLowerCase()
  const disconnected =
    status === 'error' ||
    normalizedMessage.includes('unavailable') ||
    normalizedMessage.includes('failed')

  if (disconnected) {
    return {
      containerClass: 'border-destructive/25 bg-destructive/8 text-destructive',
      label: 'Disconnected',
      lightClass: 'bg-red-500 shadow-[0_0_10px_oklch(0.63_0.26_25/70%)]',
    }
  }

  return {
    containerClass: 'border-emerald-500/25 bg-emerald-500/8 text-emerald-600 dark:text-emerald-400',
    label: 'Connected',
    lightClass: 'bg-emerald-500 shadow-[0_0_10px_oklch(0.74_0.18_154/70%)]',
  }
}
