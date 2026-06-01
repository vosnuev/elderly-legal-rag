import {
  BookOpenText,
  Clock3,
  Database,
  GitBranch,
  type LucideIcon,
} from 'lucide-react'

export type NavigationItem = {
  externalUrl?: string
  icon: LucideIcon
  label: string
  path?: string
}

export const MEMGRAPH_LAB_URL =
  import.meta.env.VITE_MEMGRAPH_LAB_URL ?? 'http://127.0.0.1:3000'

export const navigationItems: NavigationItem[] = [
  { label: 'Documents', path: '/documents', icon: BookOpenText },
  { label: 'Graph Jobs', path: '/graph-jobs', icon: GitBranch },
  { label: 'Review Queue', path: '/review-queue', icon: Clock3 },
  { label: 'Memgraph', externalUrl: MEMGRAPH_LAB_URL, icon: Database },
]
