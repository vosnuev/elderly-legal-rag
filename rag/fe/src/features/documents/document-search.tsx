import { Search } from 'lucide-react'

import { Input } from '@/components/ui/input'

type DocumentSearchProps = {
  onChange: (value: string) => void
  value: string
}

export function DocumentSearch({ onChange, value }: DocumentSearchProps) {
  return (
    <div className="flex items-center gap-2 rounded-md border bg-card px-3 py-2">
      <Search className="size-4 text-muted-foreground" aria-hidden="true" />
      <Input
        name="document-search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-8 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
        placeholder="Search stored documents"
      />
    </div>
  )
}
