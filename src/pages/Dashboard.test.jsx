import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import Dashboard from './Dashboard'
import { fetchMetrics } from '../services/api'

vi.mock('../services/api', () => ({
  fetchMetrics: vi.fn(),
}))

describe('Dashboard page', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'ResizeObserver',
      class ResizeObserverMock {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    )
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  it('shows an explicit empty state when there are no live events', async () => {
    fetchMetrics.mockResolvedValue({
      mode: 'live',
      note: 'Live local measurements.',
      empty: true,
      metrics: {
        visitors: 0,
        starts: 0,
        submissions: 0,
        completions: 0,
        reports: 0,
        leads: 0,
        qualified: 0,
        conversion_rates: {
          visitors_to_leads: null,
          starts_to_completions: null,
          completions_to_leads: null,
        },
        conversion_rate_counts: {
          visitors_to_leads: { numerator: 0, denominator: 0 },
          starts_to_completions: { numerator: 0, denominator: 0 },
          completions_to_leads: { numerator: 0, denominator: 0 },
        },
      },
      sources: [],
      funnel: [],
    })
    render(<Dashboard />)

    expect(await screen.findByText(/No live analytics events have been recorded yet/)).toBeInTheDocument()
    const qualifiedMetric = screen.getByText('Qualified leads (demo proxy)').parentElement
    expect(within(qualifiedMetric).getByText('0')).toBeInTheDocument()
    expect(screen.getAllByText('Awaiting data')).toHaveLength(3)
    expect(screen.getAllByText('0 / 0 linked records')).toHaveLength(3)
    expect(screen.getByText(/visit Assessment and submit a report/i)).toBeInTheDocument()
    expect(screen.getByText('Live local measurements.')).toBeInTheDocument()
  })

  it('shows linked conversion rates and the qualified-lead demo proxy', async () => {
    fetchMetrics.mockResolvedValue({
      mode: 'live',
      note: 'Local metrics. Linked conversion rates include tracked activity.',
      tracking_since: '2026-10-14',
      empty: false,
      metrics: {
        visitors: 6,
        starts: 4,
        submissions: 7,
        completions: 2,
        reports: 2,
        leads: 2,
        qualified: 1,
        conversion_rates: {
          visitors_to_leads: 0.5,
          starts_to_completions: 0.5,
          completions_to_leads: 0.5,
        },
        conversion_rate_counts: {
          visitors_to_leads: { numerator: 3, denominator: 6 },
          starts_to_completions: { numerator: 2, denominator: 4 },
          completions_to_leads: { numerator: 1, denominator: 2 },
        },
      },
      sources: [{ name: 'direct', value: 6 }],
      funnel: [
        { stage: 'Visitors', value: 6 },
        { stage: 'Assessment starts', value: 4 },
        { stage: 'Assessment submissions', value: 7 },
        { stage: 'Reports generated', value: 2 },
        { stage: 'Consented leads', value: 2 },
      ],
    })
    render(<Dashboard />)

    expect(await screen.findByText('Assessment submissions')).toBeInTheDocument()
    expect(screen.getByText('Qualified leads (demo proxy)')).toBeInTheDocument()
    expect(screen.getByText(/since 2026-10-14/)).toBeInTheDocument()
    expect(screen.getAllByText('50.0%')).toHaveLength(3)
    expect(screen.getByText('3 / 6 linked records')).toBeInTheDocument()
    expect(screen.getByText('2 / 4 linked records')).toBeInTheDocument()
    expect(screen.getByText('1 / 2 linked records')).toBeInTheDocument()
    expect(screen.getByText(/not NIAT’s official qualification rule/)).toBeInTheDocument()
  })

  it('shows an explicit notice instead of requesting missing preview metrics', () => {
    vi.stubEnv('VITE_FRONTEND_PREVIEW', 'true')
    render(<Dashboard />)

    expect(screen.getByRole('alert')).toHaveTextContent(/does not include the API or its database/)
    expect(fetchMetrics).not.toHaveBeenCalled()
  })

  it('shows a retryable error when the API request fails', async () => {
    fetchMetrics.mockRejectedValue(new Error('Backend unavailable'))
    render(<Dashboard />)

    expect(await screen.findByText(/Could not load live dashboard data/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})
