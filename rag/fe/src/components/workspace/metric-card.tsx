import type { ReactNode } from 'react'

import {
  Card,
  CardContent,
} from '@/components/ui/card'

type MetricCardProps = {
  icon?: ReactNode
  label: string
  value: ReactNode
}

export function MetricCard({
  icon,
  label,
  value,
}: MetricCardProps) {
  return (
    <Card 
      size="sm" 
      className="border border-border/80 rounded-2xl bg-card/65 backdrop-blur-md transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/25 group"
    >
      <CardContent className="flex items-center justify-between gap-3 p-5">
        <div className="min-w-0">
          <p className="truncate text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-none">
            {label}
          </p>
          <p className="mt-2.5 truncate text-2xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/75">
            {value}
          </p>
        </div>
        {icon ? (
          <div className="flex size-11 shrink-0 items-center justify-center rounded-xl border border-primary/10 bg-gradient-to-tr from-primary/8 to-chart-2/4 text-primary group-hover:text-chart-2 group-hover:border-chart-2/30 transition-all duration-300 shadow-sm shadow-primary/5">
            {icon}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}
