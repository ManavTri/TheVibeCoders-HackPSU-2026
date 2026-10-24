import { useState } from 'react'
import { createValidation, extractDocuments } from '../lib/api'
import type { DocumentType, ValidationReport } from '../types/api'

export function useDocuments() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function analyze(files: File[], documentTypes: DocumentType[]): Promise<ValidationReport | null> {
    setBusy(true)
    setError('')
    try {
      const documents = await extractDocuments(files, documentTypes)
      return await createValidation(documents)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Something went wrong while checking these documents.')
      return null
    } finally {
      setBusy(false)
    }
  }

  return { analyze, busy, error, setError }
}
