import type { ReactElement } from 'react'
import { Navigate } from 'react-router'

import { DocumentsPage } from '@/pages/documents-page'
import { GraphJobsPage } from '@/pages/graph-jobs-page'
import { ReviewQueuePage } from '@/pages/review-queue-page'

type IndexRoute = {
  element: ReactElement
  index: true
}

type PathRoute = {
  element: ReactElement
  path: string
}

export type AppRoute = IndexRoute | PathRoute

export const appRoutes: AppRoute[] = [
  { index: true, element: <Navigate to="/documents" replace /> },
  { path: 'documents', element: <DocumentsPage /> },
  { path: 'graph-jobs', element: <GraphJobsPage /> },
  { path: 'review-queue', element: <ReviewQueuePage /> },
]
