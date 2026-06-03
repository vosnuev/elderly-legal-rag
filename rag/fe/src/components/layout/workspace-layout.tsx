import { RefreshCw } from 'lucide-react'
import { Outlet } from 'react-router'

import { WorkspaceSidebar } from '@/components/layout/workspace-sidebar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useRagWorkspace } from '@/features/workspace/use-rag-workspace'

export function WorkspaceLayout() {
  const { message, refresh, status } = useRagWorkspace()

  return (
    <main className="min-h-screen bg-muted/30 text-foreground">
      <div className="grid min-h-screen grid-cols-[248px_1fr] max-lg:grid-cols-1">
        <WorkspaceSidebar />

        <section className="min-w-0 px-6 py-5 max-sm:px-4">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal">Document Workspace</h1>
              <p className="text-sm text-muted-foreground">{message}</p>
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={() => void refresh()}
              disabled={status === 'loading'}
            >
              <RefreshCw
                data-icon="inline-start"
                className={status === 'loading' ? 'animate-spin' : undefined}
                aria-hidden="true"
              />
              Refresh
            </Button>
          </header>

          <Separator className="my-5" />

          <Outlet />
        </section>
      </div>
    </main>
  )
}
