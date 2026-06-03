import {
  ArrowLeft,
  FileText,
  Home,
  SearchX,
} from 'lucide-react'
import {
  Link,
  useNavigate,
} from 'react-router'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
} from '@/components/ui/card'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-[calc(100vh-11rem)] items-center justify-center">
      <div className="w-full max-w-2xl">
        <div className="flex flex-col items-center text-center">
          <div className="flex size-14 items-center justify-center rounded-lg border bg-background shadow-sm">
            <SearchX className="size-7 text-muted-foreground" aria-hidden="true" />
          </div>
          <Badge variant="outline" className="mt-5">
            404
          </Badge>
          <p className="mt-4 text-7xl font-semibold tracking-normal text-muted-foreground/30 sm:text-8xl">
            404
          </p>
          <h2 className="mt-4 text-2xl font-semibold">Page not found</h2>
          <p className="mt-2 max-w-lg text-sm leading-6 text-muted-foreground">
            The requested RAG workspace route is not registered. Use the sidebar or jump back to a
            workspace page.
          </p>
        </div>

        <Card className="mt-7">
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <Button asChild>
              <Link to="/documents">
                <Home data-icon="inline-start" aria-hidden="true" />
                Documents
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/review-queue">
                <FileText data-icon="inline-start" aria-hidden="true" />
                Review Queue
              </Link>
            </Button>
          </CardContent>
        </Card>

        <div className="mt-4 flex justify-center">
          <Button type="button" variant="ghost" onClick={() => navigate(-1)}>
            <ArrowLeft data-icon="inline-start" aria-hidden="true" />
            Go Back
          </Button>
        </div>
      </div>
    </div>
  )
}
