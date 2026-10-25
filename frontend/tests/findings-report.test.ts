import { afterEach, describe, expect, it, vi } from 'vitest'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { IncompleteChecksBanner } from '../src/components/IncompleteChecksBanner'
import { getCurrentFindingsReport } from '../src/lib/backend'

describe('current findings report', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('reads skipped rule count from the findings report endpoint', async () => {
    const report = {
      findings: [],
      summary: {
        skipped_rules: 2,
        rule_errors: [
          { rule_id: 'housing.contract_vs_bill', error_class: 'NameError' },
          { rule_id: 'award.amount_mismatch', error_class: 'TypeError' },
        ],
      },
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(report), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const response = await getCurrentFindingsReport()

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/findings/report',
      expect.objectContaining({ headers: expect.any(Headers) }),
    )
    expect(response.summary.skipped_rules).toBe(2)
    expect(response.summary.rule_errors).toHaveLength(2)
  })

  it('shows an accessible warning when any checks were skipped', () => {
    const markup = renderToStaticMarkup(
      createElement(IncompleteChecksBanner, { skippedRules: 1 }),
    )

    expect(markup).toContain('role="status"')
    expect(markup).toContain('Some checks couldn’t run, so these results may be incomplete.')
  })

  it('does not show a warning when all checks completed', () => {
    const markup = renderToStaticMarkup(
      createElement(IncompleteChecksBanner, { skippedRules: 0 }),
    )

    expect(markup).toBe('')
  })
})
