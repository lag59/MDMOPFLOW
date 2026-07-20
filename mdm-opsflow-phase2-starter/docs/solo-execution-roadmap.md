# Solo Execution Roadmap

This roadmap converts the full platform plan into a solo-build sequence with milestone gates.

## Phase 1: Platform Core (4-6 weeks)
Deliverables:
- Auth lifecycle: register, login, refresh, logout, password reset
- Organization setup and profiles
- Role and permission management baseline
- Project CRUD and tenant isolation
- Bilingual framework and language switching

Exit gate:
- End-to-end tests green
- Docker startup and migrations stable
- Core tenant/admin/security flows demonstrable

## Phase 2: Operational Core (6-8 weeks)
Deliverables:
- Projects and field operations baseline
- Financial operations baseline (budget, AP/AR, billing)
- Fleet and dispatch baseline
- Safety and compliance baseline
- First tranche of AI-assisted actions

Exit gate:
- Cross-domain workflows connected (project -> cost -> field -> approval)
- Audit logging enforced for high-risk actions

## Phase 3: Intelligence and Scale (6-8 weeks)
Deliverables:
- AI intake/document intelligence workflows
- Estimating and bidding workflows
- Executive analytics and custom reports
- Integrations baseline and reconciliation
- Super-admin operations center baseline

Exit gate:
- AI workflow confidence/review loop active
- Platform-owner visibility and controls operational

## Phase 4: Mobile and Portals (6-10 weeks)
Deliverables:
- Shared mobile foundation
- Role-specific mobile experiences (driver, foreman, PM, safety, fleet)
- External portals (vendor/customer/subcontractor/employee/training)

Exit gate:
- Offline/online sync reliability
- Role-based mobile and portal access verified

## Weekly Solo Cadence
- Day 1: plan and API contracts
- Day 2-3: backend implementation and tests
- Day 4: frontend implementation and i18n
- Day 5: integration, polish, docs, and release notes

## Non-Negotiable Guardrails
- No feature considered done without:
  - tenant isolation checks
  - permission enforcement checks
  - bilingual text coverage
  - audit event capture for protected actions
  - happy-path and error-path test coverage

## Suggested First 10 Vertical Slices
1. Register -> login -> onboarding -> first project
2. Tenant user assignment with role dropdown and permissions
3. Password reset request and completion
4. MFA enroll and challenge
5. Project daily report creation and approval
6. Budget variance alert and explanation
7. Invoice intake -> OCR review -> approval
8. Dispatch board with route assignment
9. Safety incident -> corrective action workflow
10. Super-admin tenant overview and support access
