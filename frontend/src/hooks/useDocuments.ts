import { useState } from 'react'
import { createValidation, uploadDocument } from '../lib/api'
import type { DocumentRecord, DocumentType, ValidationReport } from '../types/api'

export interface UploadBatchResult {
  documents: DocumentRecord[]
  failedFiles: File[]
}

export function useDocuments() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function upload(files: File[], documentTypes: Array<DocumentType | null>): Promise<UploadBatchResult | null> {
    setBusy(true)
    setError('')
    try {
      const results = await Promise.allSettled(
        files.map((file, index) => uploadDocument(file, documentTypes[index] ?? undefined)),
      )
      const documents: DocumentRecord[] = []
      const failedFiles: File[] = []
      const failures: string[] = []

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          documents.push(result.value)
          return
        }

        failedFiles.push(files[index])
        failures.push(`${files[index].name}: ${result.reason instanceof Error
          ? result.reason.message
          : 'Upload failed.'}`)
      })

      if (failures.length > 0) {
        setError(failures.join(' '))
      }
      return { documents, failedFiles }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Something went wrong while checking these documents.')
      return null
    } finally {
      setBusy(false)
    }
  }

  async function validate(documentIds: string[]): Promise<ValidationReport | null> {
    setBusy(true)
    setError('')
    try {
      return await createValidation(documentIds)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Something went wrong while checking these documents.')
      return null
    } finally {
      setBusy(false)
    }
  }

  return { upload, validate, busy, error, setError }
}
