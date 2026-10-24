import { useEffect, useState } from 'react'
import { getInsights, getReport } from '../lib/api'
import type { Insights, ValidationReport } from '../types/api'

export function useReport(id: string) {
  const [report, setReport] = useState<ValidationReport | null>(null)
  const [insights, setInsights] = useState<Insights | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setReport(null)
    setInsights(null)
    setError('')
    Promise.all([getReport(id), getInsights(id)])
      .then(([reportResult, insightsResult]) => {
        if (!active) return
        setReport(reportResult)
        setInsights(insightsResult)
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Unable to load this report.')
      })
    return () => { active = false }
  }, [id])

  return { report, insights, error }
}
