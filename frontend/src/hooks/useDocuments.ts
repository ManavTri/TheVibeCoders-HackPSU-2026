import { useState } from 'react'
import { createValidation, uploadDocument } from '../lib/api'
import type { DocumentType, ValidationReport } from '../types/api'

export function useDocuments() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function analyze(files: File[], documentTypes: DocumentType[]): Promise<ValidationReport | null> {
    setBusy(true)
    setError('')
    try {
      const documents = await Promise.all(
        files.map((file, index) => uploadDocument(file, documentTypes[index])),
      )
      const extracted = documents.filter((document) => document.status === 'extracted')
      if (extracted.length < 2) {
        throw new Error('At least two PDFs need readable text before they can be compared. Failed uploads remain in your documents so you can review or delete them.')
      }
      return await createValidation(extracted.map((document) => document.id))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Something went wrong while checking these documents.')
      return null
    } finally {
      setBusy(false)
    }
  }

  return { analyze, busy, error, setError }
}
