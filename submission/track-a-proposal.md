# Track A — Student Acquisition Growth Proposal

## Goal

Build a measurable, consent-respecting acquisition path for prospective NIAT students, using the GrowthPilot technology-path assessment as an early value exchange. This is a proposal for a pilot; no acquisition results are claimed.

## Audience and problem hypothesis

Prospective students exploring technology education may not yet know which technology area fits their interests, experience, or stage of education. Validate this with student interviews and NIAT admissions staff before treating it as a confirmed segment need.

## Proposed journey

1. **Discover:** publish search- and social-friendly introductory content around beginner technology projects and pathway questions.
2. **Explore:** land on a focused page explaining what the short assessment does and does not do.
3. **Receive value:** answer interest, coding experience, and education-stage questions; receive three exploratory recommendations and a seven-day plan.
4. **Choose next step:** optionally provide contact information with explicit consent to request a human follow-up.
5. **Measure:** attribute anonymous visits to coarse source categories, record funnel counts, and track only consented lead events for follow-up.

## Pilot channels and tests

Start with two controllable channels: (1) organic content linking to the assessment and (2) one institution-approved student/community distribution partner. Add paid acquisition only after a baseline and consent/privacy review.

| Experiment | Hypothesis | Primary measure | Guardrail |
|---|---|---|---|
| Assessment CTA vs. general enquiry CTA | A clear, useful first step may encourage more qualified exploration. | Assessment starts per landing visitor. | Do not claim aptitude, eligibility, or job outcomes. |
| Short vs. explanatory intro | Explaining the assessment's limits may improve trust and completion. | Completion rate: completions / starts. | Keep required questions and consent understandable. |
| Project-idea emphasis | Concrete beginner project examples may make the report more actionable. | Report completion and optional lead rate. | Contact form remains optional; no pre-checked consent. |

Establish a baseline and define the traffic cohort, observation window, and minimum sample before interpreting differences. No target or result is asserted without baseline data.

## Instrumentation already present

The prototype records distinct pseudonymous browser IDs, assessment-route visits, saved completions/reports, consented leads, and coarse first-seen source categories. It exposes visitors-to-leads, starts-to-completions, and completions-to-leads rates. Qualified leads and counselling requests intentionally remain unavailable until NIAT supplies reviewed operational definitions and authorized data.

## Operations and safeguards

- Keep provider and webhook credentials server-side.
- Gemini receives only selected interest, self-reported coding experience, and education stage.
- Do not pass contact information to the report-generation provider or n8n.
- The n8n lead event is emitted only after explicit consent and includes record identifiers and consent metadata, not contact details.
- Define access controls, retention/deletion, consent wording, student-data review, attribution policy, and incident handling before a real-student pilot.
- Add staff authentication and a restricted lead-management process before real lead operations.

## Dependencies and open decisions

- NIAT confirms current programs, target segment, brand copy, privacy notice, and approved follow-up process.
- Owner defines a qualified-lead criterion (if needed) before reporting that metric.
- Confirm supported Gemini model/quota and configure a deployed n8n instance, or leave automation disabled.
- Select hosting and a production database with backups, retention, HTTPS, CORS allowlist, monitoring, and access controls.

## Decision gate

Proceed beyond a small pilot only if the assessment is understood by students, consent and data handling pass review, instrumentation is reliable, and observed funnel changes are reported with denominators and uncertainty. Stop or revise if students mistake the suggestions for formal evaluation or if privacy requirements cannot be met.
