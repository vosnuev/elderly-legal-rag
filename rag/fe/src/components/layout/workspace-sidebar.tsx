import { BookOpenText } from 'lucide-react'
import { NavLink } from 'react-router'

import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { navigationItems } from '@/routes/navigation'

export function WorkspaceSidebar() {
  return (
    <aside className="flex flex-col rounded-2xl border bg-card/45 backdrop-blur-xl p-5 shadow-xl shadow-primary/5 text-sidebar-foreground border-primary/10 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] max-lg:w-full max-lg:p-4">
      {/* Brand Logo Header */}
      <div className="flex items-center gap-3.5">
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

      <ScrollArea className="mt-8 flex-1 max-lg:mt-4">
        <nav className="flex flex-col gap-1.5 max-lg:flex-row max-lg:overflow-x-auto">
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
      </ScrollArea>
    </aside>
  )
}
