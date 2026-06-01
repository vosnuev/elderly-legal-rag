import { BrowserRouter, Route, Routes } from 'react-router'

import { WorkspaceLayout } from '@/components/layout/workspace-layout'
import { RagWorkspaceProvider } from '@/features/workspace/rag-workspace-provider'
import { NotFoundPage } from '@/pages/not-found-page'
import { appRoutes } from '@/routes/app-routes'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <RagWorkspaceProvider>
              <WorkspaceLayout />
            </RagWorkspaceProvider>
          }
        >
          {appRoutes.map((route) =>
            'index' in route ? (
              <Route key="index" index element={route.element} />
            ) : (
              <Route key={route.path} path={route.path} element={route.element} />
            ),
          )}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
