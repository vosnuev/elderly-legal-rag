import { useContext } from 'react'

import { RagWorkspaceContext } from '@/features/workspace/rag-workspace-context'

export function useRagWorkspace() {
  const context = useContext(RagWorkspaceContext)

  if (!context) {
    throw new Error('useRagWorkspace must be used within RagWorkspaceProvider.')
  }

  return context
}
