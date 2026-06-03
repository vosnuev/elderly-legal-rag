import { BookOpenText } from 'lucide-react'
import { NavLink } from 'react-router'

import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { navigationItems } from '@/routes/navigation'

export function WorkspaceSidebar() {
  return (
    <aside className="border-r bg-sidebar px-4 py-5 text-sidebar-foreground max-lg:border-b max-lg:border-r-0">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground">
          <BookOpenText className="size-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold leading-5">RAG Library</p>
          <p className="text-xs text-muted-foreground">Memgraph GraphRAG</p>
        </div>
      </div>

      <ScrollArea className="mt-8 max-lg:mt-5">
        <nav className="flex flex-col gap-1 max-lg:flex-row max-lg:overflow-x-auto">
          {navigationItems.map(({ externalUrl, label, path, icon: Icon }) => {
            const itemClassName =
              'flex h-10 shrink-0 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'

            if (externalUrl) {
              return (
                <a
                  key={externalUrl}
                  href={externalUrl}
                  target="_blank"
                  rel="noreferrer"
                  className={itemClassName}
                >
                  <Icon className="size-4" aria-hidden="true" />
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
                  cn(itemClassName, isActive && 'bg-sidebar-accent text-sidebar-accent-foreground')
                }
              >
                <Icon className="size-4" aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            )
          })}
        </nav>
      </ScrollArea>
    </aside>
  )
}
