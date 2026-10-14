import React, { useState } from 'react'
import Container from '../components/Container'
import FormField from '../components/FormField'
import Button from '../components/Button'
import Loading from '../components/Loading'
import Alert from '../components/Alert'
import { submitAssessment, trackVisit } from '../services/api'
import { getAcquisitionSource, getVisitorId } from '../services/visitor'

const initial = {
  interests: '',
  coding_experience: '',
  education_stage: '',
  lead_name: '',
  lead_email: '',
  consent: false
}

export default function Assessment(){
  const frontendPreview = import.meta.env.VITE_FRONTEND_PREVIEW === 'true'
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [apiError, setApiError] = useState(null)

  function validate(){
    const e = {}
    if(!form.interests) e.interests = 'Please select at least one interest.'
    if(!form.coding_experience) e.coding_experience = 'Please choose your coding experience.'
    if(!form.education_stage) e.education_stage = 'Please select your education stage.'
    // If user provided lead info, require consent and email
    if((form.lead_name || form.lead_email) && !form.consent) e.consent = 'Consent is required to capture lead information.'
    if(form.lead_email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.lead_email)) e.lead_email = 'Enter a valid email address.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function handleSubmit(e){
    e.preventDefault()
    setApiError(null)
    if(!validate()) return
    setLoading(true)
    setResult(null)
    try{
      const visitorId = getVisitorId()
      try {
        await trackVisit({
          visitor_id: visitorId,
          path: '/assessment',
          source: getAcquisitionSource(),
        })
      } catch (trackingError) {
        console.error('Could not confirm assessment visit tracking.', trackingError)
      }
      const payload = {
        visitor_id: visitorId,
        interests: form.interests,
        coding_experience: form.coding_experience,
        education_stage: form.education_stage,
        lead: (form.lead_name || form.lead_email) ? { name: form.lead_name, email: form.lead_email, consent: form.consent } : null
      }
      const idempotencyKey = window.crypto.randomUUID()
      const res = await submitAssessment(payload, idempotencyKey)
      setResult(res)
    }catch(err){
      console.error(err)
      setApiError(err.message || 'An error occurred')
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="pt-8 pb-12">
      <Container>
        <div className="max-w-3xl mx-auto bg-white rounded-lg shadow-md p-6">
          <h2 className="text-2xl font-semibold">Student Assessment</h2>
          <p className="text-sm text-gray-600 mt-1">Answer a few questions to generate a recommended technology path.</p>

          {frontendPreview && (
            <Alert variant="info">
              Frontend-only preview: assessment reports, saving, and lead automation are unavailable until the backend is deployed.
            </Alert>
          )}

          <form className="mt-6" onSubmit={handleSubmit} noValidate>
            <FormField label="Technology interests" id="interests" required>
              <select id="interests" value={form.interests} onChange={e=>setForm({...form, interests:e.target.value})} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" aria-invalid={Boolean(errors.interests)}>
                <option value="">Select primary interest</option>
                <option value="web">Web Development</option>
                <option value="data">Data Science</option>
                <option value="mobile">Mobile Apps</option>
                <option value="cloud">Cloud & DevOps</option>
                <option value="uiux">UI/UX & Design</option>
              </select>
              {errors.interests && <p className="mt-1 text-red-600 text-sm">{errors.interests}</p>}
            </FormField>

            <FormField label="Coding experience" required>
              <div className="flex flex-wrap gap-3" role="radiogroup" aria-label="Coding experience">
                <label className="inline-flex items-center"><input type="radio" name="exp" value="none" checked={form.coding_experience==='none'} onChange={e=>setForm({...form, coding_experience:e.target.value})} /> <span className="ml-2">None</span></label>
                <label className="inline-flex items-center"><input type="radio" name="exp" value="beginner" checked={form.coding_experience==='beginner'} onChange={e=>setForm({...form, coding_experience:e.target.value})} /> <span className="ml-2">Beginner</span></label>
                <label className="inline-flex items-center"><input type="radio" name="exp" value="intermediate" checked={form.coding_experience==='intermediate'} onChange={e=>setForm({...form, coding_experience:e.target.value})} /> <span className="ml-2">Intermediate</span></label>
                <label className="inline-flex items-center"><input type="radio" name="exp" value="advanced" checked={form.coding_experience==='advanced'} onChange={e=>setForm({...form, coding_experience:e.target.value})} /> <span className="ml-2">Advanced</span></label>
              </div>
              {errors.coding_experience && <p className="mt-1 text-red-600 text-sm">{errors.coding_experience}</p>}
            </FormField>

            <FormField label="Educational stage" id="education-stage" required>
              <select id="education-stage" value={form.education_stage} onChange={e=>setForm({...form, education_stage:e.target.value})} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" aria-invalid={Boolean(errors.education_stage)}>
                <option value="">Select stage</option>
                <option value="highschool">High School</option>
                <option value="undergrad">Undergraduate</option>
                <option value="postgrad">Postgraduate</option>
                <option value="professional">Professional / Working</option>
              </select>
              {errors.education_stage && <p className="mt-1 text-red-600 text-sm">{errors.education_stage}</p>}
            </FormField>

            <hr className="my-4" />

            <h3 className="font-semibold mb-2">Optional lead capture (consent required)</h3>
            <FormField label="Full name" id="lead-name">
              <input id="lead-name" type="text" value={form.lead_name} onChange={e=>setForm({...form, lead_name:e.target.value})} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
            </FormField>

            <FormField label="Email" id="lead-email">
              <input id="lead-email" type="email" value={form.lead_email} onChange={e=>setForm({...form, lead_email:e.target.value})} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" aria-invalid={Boolean(errors.lead_email)} />
              {errors.lead_email && <p className="mt-1 text-red-600 text-sm">{errors.lead_email}</p>}
            </FormField>

            <div className="mb-4">
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={form.consent} onChange={e=>setForm({...form, consent:e.target.checked})} />
                <span className="text-sm">I consent to being contacted about relevant programs and offers.</span>
              </label>
              {errors.consent && <p className="mt-1 text-red-600 text-sm">{errors.consent}</p>}
            </div>

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={loading || frontendPreview}>{loading ? <Loading label="Submitting..." /> : 'Get My Report'}</Button>
              <button type="button" className="text-sm text-gray-600 underline" onClick={()=>{setForm(initial); setErrors({}); setResult(null); setApiError(null)}}>Reset</button>
            </div>
          </form>

          <div className="mt-6" aria-live="polite">
            {apiError && <Alert variant="error">{apiError}</Alert>}
            {result && (
              <div className="mt-4 space-y-4">
                <Alert variant="success">
                  Your report was generated and saved. {result.automation
                    ? `Lead workflow status: ${result.automation.status}.`
                    : ''}
                </Alert>
              <div className="bg-gray-50 border rounded p-4">
                <h4 className="font-semibold">{result.report?.title || 'Report'}</h4>
                <p className="text-sm text-gray-700 mt-2">{result.report?.summary}</p>
                {result.report?.recommendations ? (
                  <div className="mt-4 space-y-4">
                    <section>
                      <h5 className="font-medium">Three fields to explore</h5>
                      <div className="mt-2 grid gap-3">
                        {result.report.recommendations.map((recommendation) => (
                          <article key={recommendation.field} className="rounded border bg-white p-3">
                            <h6 className="font-medium">{recommendation.field}</h6>
                            <p className="mt-1 text-sm text-gray-700">{recommendation.reason}</p>
                            <p className="mt-2 text-sm"><span className="font-medium">Project idea:</span> {recommendation.project_idea}</p>
                          </article>
                        ))}
                      </div>
                    </section>
                    <section>
                      <h5 className="font-medium">Seven-day exploration plan</h5>
                      <ol className="mt-2 list-decimal list-inside space-y-1 text-sm text-gray-700">
                        {result.report.seven_day_plan?.map((day) => (
                          <li key={day.day}><span className="font-medium">Day {day.day}:</span> {day.activity}</li>
                        ))}
                      </ol>
                    </section>
                    <section>
                      <h5 className="font-medium">Suggested next steps</h5>
                      <ul className="mt-2 list-disc list-inside text-sm text-gray-700">
                        {result.report.next_steps?.map((step) => <li key={step}>{step}</li>)}
                      </ul>
                    </section>
                  </div>
                ) : (
                  <div className="mt-3">
                    <h5 className="font-medium">Recommended path</h5>
                    <ul className="list-disc list-inside text-sm text-gray-700">
                      {(result.report?.recommended_path || []).map((recommendation) => (
                        <li key={recommendation}>{recommendation}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="mt-3 text-xs text-gray-500">
                  {result.report?.generation_mode === 'gemini'
                    ? `AI-generated with Google Gemini${result.report.model ? ` (${result.report.model})` : ''}.`
                    : 'Rule-based development recommendation; not AI-generated.'}
                </p>
              </div>
              </div>
            )}
          </div>

        </div>
      </Container>
    </div>
  )
}
