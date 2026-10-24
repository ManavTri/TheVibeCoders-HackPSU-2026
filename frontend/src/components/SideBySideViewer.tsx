import type { DocumentSummary } from '../types/api'
import { DocumentCard } from './DocumentCard'

export function SideBySideViewer({ documents }: { documents: DocumentSummary[] }) {
  return (
    <div className="side-by-side">
      {documents.map((document) => <DocumentCard key={document.id} document={document} />)}
    </div>
  )
}
