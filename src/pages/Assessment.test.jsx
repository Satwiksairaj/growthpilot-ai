import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Assessment from './Assessment'
import { submitAssessment, trackVisit } from '../services/api'

vi.mock('../services/api', () => ({
  submitAssessment: vi.fn(),
  trackVisit: vi.fn(),
}))

vi.mock('../services/visitor', () => ({
  getVisitorId: vi.fn(() => 'visitor-1'),
  getAcquisitionSource: vi.fn(() => 'direct'),
}))

const generatedReport = {
  assessment_id: 'assessment-1',
  report: {
    title: 'Your technology exploration report',
    summary: 'Explore fields that match the interests you selected.',
    generation_mode: 'rule-based-development',
    recommendations: [
      { field: 'Web Development', reason: 'Matches your interest in web.', project_idea: 'Make a small website.' },
      { field: 'Software Engineering', reason: 'Build fundamentals.', project_idea: 'Build a small app.' },
      { field: 'Human-Centered Technology', reason: 'Explore user needs.', project_idea: 'Prototype a student tool.' },
    ],
    seven_day_plan: Array.from({ length: 7 }, (_, index) => ({
      day: index + 1,
      activity: `Explore a concept on day ${index + 1}.`,
    })),
    next_steps: ['Choose one project.', 'Reflect on your interests.'],
  },
}

function renderAssessment() {
  render(
    <MemoryRouter>
      <Assessment />
    </MemoryRouter>,
  )
}

function completeRequiredFields() {
  fireEvent.change(screen.getByDisplayValue('Select primary interest'), { target: { value: 'web' } })
  fireEvent.click(screen.getByLabelText('Beginner'))
  fireEvent.change(screen.getByDisplayValue('Select stage'), { target: { value: 'undergrad' } })
}

describe('Assessment page', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('submits assessment and renders the structured report', async () => {
    trackVisit.mockResolvedValue(null)
    submitAssessment.mockResolvedValue(generatedReport)
    renderAssessment()
    completeRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: 'Get My Report' }))

    expect(await screen.findByText('Your technology exploration report')).toBeInTheDocument()
    expect(screen.getByText('Three fields to explore')).toBeInTheDocument()
    expect(screen.getByText('Day 7:')).toBeInTheDocument()
    expect(screen.getByText('Rule-based development recommendation; not AI-generated.')).toBeInTheDocument()
    expect(submitAssessment).toHaveBeenCalledWith(
      expect.objectContaining({
        visitor_id: 'visitor-1',
        interests: 'web',
        coding_experience: 'beginner',
        education_stage: 'undergrad',
        lead: null,
      }),
      expect.any(String),
    )
    expect(trackVisit).toHaveBeenCalledWith({
      visitor_id: 'visitor-1',
      path: '/assessment',
      source: 'direct',
    })
  })

  it('requires consent before sending optional lead details', async () => {
    renderAssessment()
    completeRequiredFields()
    fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'student@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: 'Get My Report' }))

    expect(await screen.findByText('Consent is required to capture lead information.')).toBeInTheDocument()
    expect(submitAssessment).not.toHaveBeenCalled()
  })

  it('shows backend errors without presenting a successful report', async () => {
    trackVisit.mockResolvedValue(null)
    submitAssessment.mockRejectedValue(new Error('The report service is unavailable.'))
    renderAssessment()
    completeRequiredFields()
    fireEvent.click(screen.getByRole('button', { name: 'Get My Report' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('The report service is unavailable.')
    })
    expect(screen.queryByText('Three fields to explore')).not.toBeInTheDocument()
  })
})
