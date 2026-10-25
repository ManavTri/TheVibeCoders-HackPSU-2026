import { useRef, useState } from 'react'

export function DocumentDropzone({ onFilesAdded }) {
  const inputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFiles = (files) => {
    if (!files || files.length === 0) return
    onFilesAdded(Array.from(files))
  }

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setIsDragging(false)
        handleFiles(event.dataTransfer.files)
      }}
      className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
        isDragging
          ? 'border-neutral-500 bg-neutral-900/80'
          : 'border-neutral-700 bg-[#0a0d11] hover:border-neutral-500 hover:bg-[#0f141a]'
      }`}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        multiple
        className="hidden"
        onChange={(event) => handleFiles(event.target.files)}
      />
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-neutral-800 text-3xl text-white">
        ⤴
      </div>
      <p className="mt-5 text-lg font-medium text-white">Drop files here</p>
      <p className="mt-2 text-sm text-slate-400">Upload scholarship letters, tuition bills, or study-abroad quotes as PDFs.</p>
      <button
        type="button"
        className="mt-5 rounded-full border border-neutral-600 bg-neutral-800 px-4 py-2 text-sm font-medium text-white"
      >
        Select documents
      </button>
    </div>
  )
}
