# Loom Walkthrough Script (Target: 2:30–2:50)

Keep the recording under three minutes. Replace any bracketed status only with something verified in the recording.

## 0:00–0:20 — Context

“GrowthPilot AI is a prototype for helping prospective students explore technology pathways while giving an institution a measurable acquisition funnel. The recommendations are exploratory—not an aptitude test, admission decision, or employment promise.”

## 0:20–0:45 — Landing and assessment

“Here is the landing page and the path into the assessment. It asks about technology interest, coding experience, and education stage. Required answers are validated before submission.”

## 0:45–1:15 — Report and consent

“The report includes three technology directions, project ideas, a seven-day exploration plan, and next steps. [State the mode actually displayed: Gemini-generated or rule-based development.] Lead capture is optional and only submitted with explicit consent.”

## 1:15–1:45 — Dashboard

“The dashboard reads counts from the local SQLite backend. It distinguishes visitors, starts, completions, persisted reports, and consented leads, and shows the funnel and coarse acquisition source. These are development measurements, not sample claims or production analytics. Qualified leads remain unavailable until there is an approved definition.”

## 1:45–2:15 — Architecture and safeguards

“The React frontend calls a separate FastAPI service. The backend validates and persists data, and an idempotency key helps avoid duplicate submissions on retry. Gemini credentials stay server-side; only the three assessment answers go to the report provider. Contact details are not sent to Gemini or n8n.”

## 2:15–2:40 — Status and next steps

“The repository includes automated tests and an importable, optional n8n workflow. [State whether a live n8n instance was actually tested.] Before a real pilot, the institution still needs to approve privacy and retention policies, define any lead qualification rules, and deploy the services with secure storage, HTTPS, and monitoring. The next step is a small measured pilot with a verified baseline.”
