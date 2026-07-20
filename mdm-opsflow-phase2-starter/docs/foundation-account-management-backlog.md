# Foundation and Account Management Backlog

Planning horizon: 6 sprints
Total estimate: 121 points
Target screen count: 30 screens

## Sprint 1 - Access and Identity Core (23 points)
Goal: baseline auth and account lifecycle is functional end-to-end.

1. Login page and session bootstrap (3)
2. Registration page and API integration (3)
3. Forgot password request flow (3)
4. Reset password completion flow (3)
5. Auth API hardening for token lifecycle and logout (3)
6. Auth tests: register, login, me, refresh, logout (5)
7. UX polish for auth errors and loading states (3)

Exit criteria:
- User can register, login, logout, refresh token
- User can request and complete password reset
- Auth tests pass in CI

## Sprint 2 - Organization and Profiles (21 points)
Goal: tenant and profile foundations are complete.

1. Organization setup wizard scaffold (3)
2. Company details and modules step persistence (5)
3. Setup completion step with first admin assignment (5)
4. Company profile view and edit (3)
5. User profile view and edit (3)
6. Tenant setup and profile tests (2)

Exit criteria:
- New user can set up an organization
- Company profile and user profile are editable
- Onboarding creates required tenant records

## Sprint 3 - Roles, Permissions, and Assignment (24 points)
Goal: account governance and team assignment are enforceable.

1. Roles list and role details pages (5)
2. Create and edit role screen (5)
3. Permission matrix by module (5)
4. User-role assignment UI and API integration (5)
5. Authorization tests for role and permission boundaries (4)

Exit criteria:
- Tenant admins can manage roles and assignments
- Effective permissions are enforced in APIs
- Permission edge cases are tested

## Sprint 4 - Preferences and Notifications (16 points)
Goal: user preference and communication controls are saved and respected.

1. Language preference page and persistence (3)
2. Notification channels settings (4)
3. Notification rules by event type (4)
4. Digest and quiet-hours configuration (3)
5. Preference tests and validation (2)

Exit criteria:
- User language preference persists across sessions
- Notification preferences can be configured and retrieved

## Sprint 5 - Subscription and Billing (20 points)
Goal: commercial account management is visible and editable.

1. Subscription overview page (4)
2. Plan and seat management page (5)
3. Billing method and invoice management (6)
4. Billing history and receipts page (3)
5. Billing API and contract tests (2)

Exit criteria:
- Tenant can view subscription state and billing history
- Plan and seat updates are reflected in account state

## Sprint 6 - Integrations, Audit, and MFA Enforcement (17 points)
Goal: operational trust and advanced account security are complete.

1. Integrations hub page and connector status (5)
2. Audit history page with filtering (4)
3. MFA setup and enrollment page (3)
4. MFA challenge flow and step-up enforcement (3)
5. Audit and MFA tests (2)

Exit criteria:
- Audit history captures high-value account actions
- MFA can be enabled and enforced for protected actions
- Integrations page reports connector health

## Story Point Scale
- 1 point: tiny, isolated change
- 2-3 points: small feature or endpoint
- 5 points: medium cross-layer item (UI + API + tests)
- 8 points: large or uncertain item

## Dependencies and Ordering Rules
1. Auth core before profile, preferences, and billing
2. Organization setup before role assignment
3. Role and permission engine before governance UI completion
4. Audit event contracts before final operational sign-off

## Risk Flags
- MFA delivery integration and recovery flow complexity
- Billing provider and webhook edge cases
- Permission matrix drift between frontend labels and backend enforcement
- Notification fan-out and preference precedence
