import { useEffect, useState } from 'react'
import { getCurrentFindingsReport, getInsights, getReport } from '../lib/api'
import type { CurrentFindingsReport, Insights, ValidationReport } from '../types/api'

export function useReport(id: string) {
  const [report, setReport] = useState<ValidationReport | null>(null)
  const [insights, setInsights] = useState<Insights | null>(null)
  const [currentFindingsReport, setCurrentFindingsReport] = useState<CurrentFindingsReport | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setReport(null)
    setInsights(null)
    setCurrentFindingsReport(null)
    setError('')
    Promise.all([getReport(id), getInsights(id), getCurrentFindingsReport()])
      .then(([reportResult, insightsResult, findingsReportResult]) => {
        if (!active) return
        setReport(reportResult)
        setInsights(insightsResult)
        setCurrentFindingsReport(findingsReportResult)
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : 'Unable to load this report.')
      })
    return () => { active = false }
  }, [id])

  return { report, insights, currentFindingsReport, error }
}
