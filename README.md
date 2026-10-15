# GrowthPilot AI

GrowthPilot AI is a student acquisition and growth analytics demo for exploring technology pathways. It combines a React frontend, FastAPI backend, SQLite persistence, optional Google Gemini report generation, and an n8n lead-follow-up workflow.

> The app is deployed as a demo, not a production-ready student information system. The hosted services currently use temporary SQLite storage, so data may be lost on restart or redeploy. Reports use the labeled rule-based fallback unless a configured Gemini request succeeds. Do not enter real student or lead data.

## Features

- Responsive landing page and student technology-interest assessment.
- Structured report with three technology recommendations, project ideas, a seven-day plan, and next steps.
- Optional lead form; name/email collection requires explicit consent.
- Live dashboard with visitors, assessment starts/completions, persisted reports, consented leads, conversion rates, funnel, and acquisition-source charts. No seeded sample metrics.
- SQLite persistence, server-side validation, idempotent assessment submission, and aggregate automation status.
- Optional, authenticated n8n webhook for consented lead events. Lead contact details are not sent to Gemini or n8n.

## Project layout

```text
growthpilot-ai/
├── backend/
│   ├── app/main.py              # FastAPI routes, SQLite persistence, analytics, webhook dispatch
│   ├── app/ai_reports.py        # Gemini integration and labeled rule-based report
│   ├── tests/                   # API, data, automation, and report tests
│   ├── Dockerfile               # Backend container
│   └── requirements.txt
├── n8n/
│   └── growthpilot-consented-lead.json
├── submission/                  # Challenge research and presentation materials
├── src/
│   ├── components/              # Shared UI and visit tracking
│   ├── pages/                   # Landing, assessment, dashboard
│   └── services/api.js          # Frontend API calls
├── .env.example                 # Safe configuration template; contains no secrets
├── package.json
└── vite.config.ts               # Vite API proxy for local development
```

## Run locally (Windows / PowerShell)

Run frontend and backend in separate terminals from the project root.

### Frontend

```powershell
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. In development, Vite proxies `/api` to `http://127.0.0.1:8000`.

### Backend

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Backend health endpoint: `http://127.0.0.1:8000/api/health`.

## Configuration

Copy `.env.example` to the project-root `.env` and set only the values needed. `.env` is ignored by Git; never place secrets in frontend variables, source files, screenshots, or commits. Restart the relevant service after changing configuration.

| Variable | Used by | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Backend | Private provider key. Omit to use the labeled rule-based development report. |
| `GEMINI_MODEL` | Backend | Gemini model identifier available to your account. Defaults to `gemini-3.5-flash-lite` in `.env.example`; required when a key is set. |
| `GEMINI_TIMEOUT_SECONDS` | Backend | Provider request timeout, from 1 to 60 seconds; default 25. |
| `GROWTHPILOT_DB_PATH` | Backend | SQLite database path; defaults to `backend/growthpilot.db`. |
| `CORS_ORIGINS` | Backend | Comma-separated allowed browser origins. Local Vite origins are the development default. |
| `N8N_WEBHOOK_URL` | Backend | Active n8n production webhook URL. |
| `N8N_WEBHOOK_SECRET` | Backend | Shared bearer secret, stored only in backend and n8n credential configuration. |
| `VITE_API_BASE_URL` | Frontend build | Backend API origin for a deployed frontend; leave unset for the local Vite proxy. Must not contain secrets. |

If `GEMINI_API_KEY` is absent, deterministic rules generate the report and the UI identifies it as `rule-based-development`. If the key is configured but the model/provider request fails or the response is invalid, the API returns an error; it does not silently claim a rule-based report is AI-generated. Gemini receives only the selected interest, self-reported coding experience, and education stage.

Live Gemini report generation was verified with `gemini-3.5-flash-lite` during development. Model availability and quota can change; check provider status if requests fail. The integration tests use mocks and do not consume provider quota.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Backend and safe configuration status (no secret values). |
| `POST` | `/api/visits` | Record a pseudonymous visitor, page path, and coarse acquisition category. |
| `POST` | `/api/assessments` | Validate inputs, generate and save a report, and save a lead only with consent. Accepts optional `Idempotency-Key`. |
| `GET` | `/api/metrics` | Return SQLite-derived metrics, definitions, funnel, sources, and automation totals. |
| `GET` | `/api/automation/status` | Aggregate automation configuration and status only. |

Assessment enums:

- Interests: `web`, `data`, `mobile`, `cloud`, `uiux`
- Coding experience: `none`, `beginner`, `intermediate`, `advanced`
- Education stage: `highschool`, `undergrad`, `postgrad`, `professional`
- Optional lead object: name and/or email plus `consent: true`

The optional idempotency key prevents duplicate assessment/lead records on client retries. Reusing the key with different data returns `409`. A provider failure returns `503` and does not count as a successfully persisted report.

## Dashboard definitions

- **Visitors:** distinct pseudonymous browser IDs recorded in local storage and SQLite.
- **Assessment starts:** distinct visitors recorded on `/assessment`.
- **Assessment submissions:** all saved assessment records, including legacy records without a persisted report.
- **Completions / reports:** assessments with a successfully generated and persisted report (Gemini or labeled rule-based).
- **Leads:** consented contact records associated with a saved assessment.
- **Qualified leads:** a clearly labeled development proxy: high-school stage, consented name or email, and a successfully saved report. This is not NIAT's official qualification rule. Counselling requests are not configured.
- **Conversion rates:** browser visitor IDs are attached to assessment submissions. Visitor-to-lead, assessment-start-to-report, and report-to-consented-lead rates use records since linked tracking was enabled; historical unlinked activity is excluded. The dashboard shows linked numerator/denominator counts and says "Awaiting data" when there is no denominator; it does not substitute a fabricated 0% rate.
- **Sources:** approximate first-seen category (`direct`, `organic`, `paid`, `referral`, `social`) inferred from referrer/UTM data.
- The chart shows total local activity counts; linked conversion rates use only the newer tracked cohort and are not calculated from these lifetime totals.

These are local SQLite measurements, not production analytics. The database may contain prior development/test activity; clear or replace it before presenting counts as a fresh demo. The default database `backend/growthpilot.db` is ignored by Git.

## Optional n8n setup

The importable workflow at [n8n/growthpilot-consented-lead.json](./n8n/growthpilot-consented-lead.json) validates consented lead events, prepares a staff-review follow-up task record, and returns an event-specific acknowledgement. Configure an n8n instance to use it:

1. Import the workflow JSON into n8n.
2. Create an **HTTP Header Auth** credential with header name `Authorization` and use the shared secret configured as `N8N_WEBHOOK_SECRET`; do not put the secret in source files. Select this credential on the webhook node.
   Send the configured shared secret unchanged in the Authorization header; no prefix is required.
3. Activate the workflow and copy its **production** webhook URL (not its test URL).
4. Set that URL as `N8N_WEBHOOK_URL` and the same secret as `N8N_WEBHOOK_SECRET` in the backend environment.
5. Keep successful execution data enabled if n8n execution history is the intended audit trail. The workflow JSON enables save-on-success.
6. Submit a test assessment with explicit lead consent. A configured automation is considered successful only when n8n responds with `{ "accepted": true, "event_id": "<matching event ID>" }`.

The backend records an automation event after saving the lead, then tries delivery synchronously up to two times. Delivery failure does not roll back the assessment/lead, but there is no background worker or scheduled retry. The webhook payload contains record IDs, consent state, and timestamp—not name, email, assessment answers, or report text. The workflow is inactive by default; a local n8n instance was verified during development; this does not verify a separately deployed instance.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -t backend -v
npm test
npm run build
```

Provider tests use mocks and do not consume Gemini quota. A passing test suite does not establish live provider or workflow availability.

## Container deployment preparation

The backend Dockerfile runs as a non-root user and expects persistent storage at `/var/lib/growthpilot`. From the project root, build using the backend as the build context:

```powershell
docker build -t growthpilot-api -f backend\Dockerfile backend
docker run --rm -p 8000:8000 `
  -e GROWTHPILOT_DB_PATH=/var/lib/growthpilot/growthpilot.db `
  -e CORS_ORIGINS=https://your-frontend.example `
  -v growthpilot-data:/var/lib/growthpilot `
  growthpilot-api
```

Supply provider and n8n secrets through the host/deployment secret manager, never as image build arguments. Configure the frontend build with `VITE_API_BASE_URL` pointing at the deployed API, set `CORS_ORIGINS` to the exact frontend origin, configure HTTPS, and provide persistent-volume backups/retention. This is deployment preparation only; hosting, HTTPS, backups, and production service operation have not been performed or verified.

### Render Blueprint

The root `render.yaml` defines a free API service and a free n8n service; the frontend is hosted separately on Vercel. Free Render services can sleep when idle and do not include persistent disks. The current deployment uses SQLite for both API and n8n, so their data and workflows may be lost when a service restarts or is redeployed. This temporary setup is for evaluation only, not real student or lead data.

To make data durable, configure Supabase Postgres before switching either service from SQLite. Provide the Supabase connection details through Render's secret manager; keep database credentials out of Git, source files, and chat. Render generates the n8n encryption key and shared webhook secret. Enter the Gemini API key only in Render's secret prompt.

After the services are deployed, open the n8n editor, create an HTTP Header Auth credential named `GrowthPilot Shared Secret` with header `Authorization` and the generated shared secret, import `n8n/growthpilot-consented-lead.json`, select that credential on the webhook, and activate the workflow. The Blueprint references the generated shared secret for both API and n8n. Configure Vercel's production `VITE_API_BASE_URL` to the Render API origin, remove the frontend-only preview flag, and redeploy. Verify backend health, dashboard metrics, and a synthetic consented test lead end to end before sharing it. Free services may sleep, have usage limits, or restart; do not store real student data in this temporary setup.

### Vercel frontend

Vercel hosts the frontend at `https://growthpilot-ai-kohl.vercel.app`. The committed `.env.production` keeps the app in a safe frontend-only preview until the API is connected; it displays a notice, disables assessment submission, skips visit tracking, and avoids requesting missing metrics. Remove that preview flag and configure `VITE_API_BASE_URL` in Vercel's production environment only after the API is deployed and health-checked. Use durable Postgres before collecting real data.

## Submission materials

- [Research audit](./submission/research-audit.md)
- [Track A growth proposal](./submission/track-a-proposal.md)
- [Reflection template](./submission/reflection-template.md)
- [Three-minute walkthrough script](./submission/loom-script.md)

## Known limitations and production requirements

- No student accounts, staff authentication/permissions, or staff lead-management UI.
- No lead qualification rules; qualified lead and counselling counts are intentionally unavailable.
- SQLite is for local/single-instance evaluation, not a configured multi-instance production database.
- No durable hosted database, backup/retention policy, or operational monitoring has been set up.
- Acquisition attribution is approximate and needs a privacy-reviewed analytics policy.
- Review applicable privacy, security, accessibility, and student-data rules before handling real student or lead information.
- Configure and verify supported Gemini model access and n8n workflow operation in the target environment.
