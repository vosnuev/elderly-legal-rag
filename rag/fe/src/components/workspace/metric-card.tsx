import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type MetricCardProps = {
  icon?: ReactNode
  label: string
  value: ReactNode
  className?: string
}

export function MetricCard({
  icon,
  label,
  value,
  className,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "border border-border/45 rounded-xl bg-card/75 backdrop-blur-md transition-all duration-300 hover:border-accent/35 hover:bg-muted/10 hover:shadow-[0_2px_12px_rgba(0,0,0,0.02)] hover:-translate-y-[0.5px] group flex items-center justify-between gap-4 p-3 px-4.5 h-15 select-none",
        className
      )}
    >
      <div className="min-w-0">
        <p className="truncate text-[8px] font-black text-muted-foreground/60 uppercase tracking-widest leading-none pl-0.5">
          {label}
        </p>
        <p className="mt-1.5 truncate text-lg font-black tracking-tight text-foreground/90 leading-none">
          {value}
        </p>
      </div>
      {icon ? (
        <div className="flex size-7.5 shrink-0 items-center justify-center rounded-lg border border-accent/15 bg-accent/5 text-accent group-hover:text-accent group-hover:border-accent/35 group-hover:bg-accent/10 transition-all duration-300 shadow-sm shadow-accent/5">
          {icon}
        </div>
      ) : null}
    </div>
  )
}
