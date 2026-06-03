import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { useState } from 'react'

type DocumentSearchProps = {
  onChange: (value: string) => void
  value: string
}

export function DocumentSearch({ onChange, value }: DocumentSearchProps) {
  const [focused, setFocused] = useState(false)

  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-xl border border-border/45 bg-card/65 backdrop-blur-md px-3.5 py-1.5 transition-all duration-300 select-none w-full",
        focused
          ? "border-accent/45 shadow-[0_2px_12px_oklch(var(--color-accent)/4%)] bg-muted/5"
          : "hover:border-border/80"
      )}
    >
      <Search
        className={cn(
          "size-3.5 transition-colors duration-300 shrink-0",
          focused ? "text-accent" : "text-muted-foreground/60"
        )}
        aria-hidden="true"
      />
      <Input
        name="document-search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="h-7 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0 text-xs font-semibold placeholder:text-muted-foreground/45 text-foreground/95"
        placeholder="Search stored documents by name, title, or content..."
      />
    </div>
  )
}
