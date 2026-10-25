interface IncompleteChecksBannerProps {
  skippedRules: number
}

export function IncompleteChecksBanner({ skippedRules }: IncompleteChecksBannerProps) {
  if (skippedRules <= 0) return null

  return (
    <p className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="status">
      Some checks couldn’t run, so these results may be incomplete.
    </p>
  )
}
