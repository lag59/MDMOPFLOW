# MDM OpsFlow Full Platform Master Plan

## Scope Summary
This document consolidates your full product vision across web, mobile, and platform-owner operations.

### Estimated Screen Volume
- Core web platform: 230-320 screens
- Mobile application: 150-200 screens
- Super-admin platform: 100-125 screens
- Total product surface: 480-645 screens

## Product Domains

### 1) Foundation and Account Management (25-35 screens)
- Login
- Account registration
- MFA
- Password reset
- Organization setup
- Company profile
- User profile
- Language preference
- Notification settings
- Role management
- Permissions
- Subscription management
- Billing
- Integrations
- Audit history

### 2) Executive and Analytics (20-30 screens)
- Executive dashboard
- Company health
- Revenue dashboard
- Cost dashboard
- Project portfolio
- Cash-flow forecast
- Backlog
- Estimate win rate
- Budget variance
- Labor performance
- Equipment utilization
- Safety performance
- Compliance score
- AI recommendations
- Custom reports

### 3) Projects and Field Operations (35-45 screens)
- Project list and project creation
- Project overview and team
- Budget, cost codes, contracts, change orders
- Daily reports, production, documents, photos
- Schedules, tasks, RFIs, submittals
- Materials, field activity, weather impacts, closeout

### 4) AI Intake and Document Intelligence (25-35 screens)
- Batch and drag-drop intake
- Email intake and scan queue
- Classification and OCR extraction
- Ticket/invoice/contract/certificate review
- Duplicate detection and entity matching
- Low-confidence review, bulk approval, exceptions
- Processing history, extraction audit, correction learning

### 5) Estimating and Bidding (25-35 screens)
- Opportunity pipeline, bid invitations
- Estimate list and estimate builder
- Plan upload and quantity takeoff
- Labor/equipment/material costs
- Trucking calculations and subcontractor quotes
- Markup/exclusions/risk review
- AI estimate assistant and estimate comparison
- Proposal generation, submission, bid analysis, award/loss

### 6) Financial Operations (30-40 screens)
- Budgets, committed costs, actual costs
- Forecast cost to complete
- Purchase orders and material orders
- Accounts payable, invoices, customer billing
- Vendor payments, payroll prep, time approval
- Expense review, QuickBooks sync, reconciliation, WIP reporting

### 7) Fleet, Equipment, GPS, and Dispatch (30-40 screens)
- Fleet dashboard and map
- Live GPS and dispatch board
- Route planning, trucks, drivers, equipment
- Inspections, maintenance, work orders, rentals
- Telematics, fuel, utilization, machine assignments
- DOT compliance, ELD records, FMCSA documentation

### 8) Safety, Training, and Compliance (25-35 screens)
- Safety dashboard
- Employee compliance profile
- OSHA/CPR/certification records
- Toolbox talks, JHAs, inspections
- Incidents, near misses, corrective actions
- SDS library, site orientations, compliance rules
- Expiring credentials, training calendar, rosters, certificates

### 9) Portals (15-25 screens)
- Vendor portal
- Customer portal
- Subcontractor portal
- Employee portal
- Training portal

### 10) Mobile Role-Based Experience (150-200 screens)
Shared:
- Login, language, profile, notifications, offline status, sync, AI assistant, scanner, camera upload, signature, settings

Driver:
- Clock in/out, route, dispatch details, GPS trip, load entry, ticket scan, delivery confirmation, inspection, fuel, hours summary, incident report

Foreman:
- Crew attendance, daily plan, production entry, equipment assignment, material request, ticket approval, daily report, toolbox talk, safety observation, photo docs, time approval

Superintendent and PM:
- Project dashboard, budget summary, schedule, production, pending approvals, change orders, field reports, AI insights, issue escalation

Safety:
- Inspections, toolbox talks, JHAs, incident reporting, near misses, training validation, certificate scanning, corrective actions

Equipment and fleet:
- Assignment, inspection, maintenance request, machine hours, fuel, GPS, fault alerts, rental return

### 11) Super-Admin Platform (100-125 screens)
Platform management:
- Tenant list/profile, user management, subscriptions, plans, billing, feature flags, trials, limits, storage, account suspension, support access

AI operations center:
- Processing volume, OCR accuracy, model performance, prompt versions, confidence trends, extraction failures, correction queue, templates, field accuracy, processing costs, routing, escalation rules, AI audit

System operations:
- Platform health, API performance, worker queues, failed jobs, integrations, logs, security events, database/storage health, deployment status, incident management

Customer success:
- Onboarding progress, adoption metrics, health, support history, training status, renewal risk, feature usage, feedback, implementation milestones

## Design System Program

### Foundations
- Color, typography, spacing, grid, shadows, borders, motion
- Accessibility
- Light and dark modes
- English and Spanish
- Responsive behavior

### Core Components
- Inputs, selectors, date controls, data tables and grids
- Cards, tabs, modals, drawers, notifications
- Filters, search, file upload
- Maps and charts
- Approval controls, signatures
- AI panels and confidence indicators
- Audit timelines

### Construction-Specific Components
- Project status card
- Budget health card
- Cost-code table
- Ticket review panel
- OCR confidence row
- Equipment and truck cards
- Dispatch board and GPS marker
- Certification badge and compliance alert
- Estimate worksheet
- Change-order panel
- Inspection checklist
- Daily report builder

## Template Strategy
Build 25-35 reusable templates to avoid one-off layouts.

Core template set:
1. Dashboard template
2. List template
3. Record detail template
4. Creation wizard
5. Bulk-upload template
6. AI review template
7. Approval queue template
8. Map and dispatch template
9. Budget template
10. Analytics template
11. Document viewer template
12. Timeline and audit template
13. Settings template
14. Portal template
15. Mobile task template
16. Mobile scan template
17. Mobile checklist template
18. Admin operations template

## Bilingual-First Requirements
- English and Spanish designed together from day one
- Support longer Spanish labels without layout break
- Regional terminology support
- Bilingual notifications and reports
- User-level language preference
- Company default language
- Instant language switching
- Mixed-language AI prompts when needed

## Visual Direction
- Modern, clean, spacious, premium, calm, field-friendly
- Light mode: off-white base, white cards, navy text, restrained orange accents, blue for AI/analytics
- Dark mode: deep navy base, elevated dark panels, high-contrast data, subtle blue/orange accents
- Interaction: minimal clicks, quick actions, smart defaults, inline edits, autosave, shortcuts, responsive tables, clear empty/error states

## AI Experience Requirements
- Persistent AI Copilot from every screen
- AI action cards for proactive risks and recommendations
- AI transparency with source, confidence, reasoning summary, impacted records, financial impact, and approval requirement

## Recommended Build Sequence
1. Foundation and account management
2. Project and field operations baseline
3. Financial operations core
4. Estimating and bidding baseline
5. Fleet and dispatch baseline
6. Safety and compliance baseline
7. AI intake and document intelligence
8. Executive analytics and reporting
9. External portals
10. Mobile role-based expansions
11. Super-admin operations center

## Solo Execution Guidance
- Build reusable templates before deep domain breadth
- Use vertical slices: one complete workflow at a time (UI, API, tests, telemetry)
- Keep bilingual and role-based access in every acceptance criteria
- Add AI transparency metadata on all AI-assisted actions from the start
