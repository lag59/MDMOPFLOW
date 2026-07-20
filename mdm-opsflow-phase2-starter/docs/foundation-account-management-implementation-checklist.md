# Foundation and Account Management Implementation Checklist

Scope alignment: login, registration, MFA, password reset, organization setup, company profile, user profile, language preference, notification settings, role management, permissions, subscription management, billing, integrations, audit history.

## Backend API Checklist

### Authentication and Identity
- [ ] POST /api/auth/register
- [ ] POST /api/auth/login
- [ ] GET /api/auth/me
- [ ] POST /api/auth/refresh
- [ ] POST /api/auth/logout
- [ ] POST /api/auth/password/forgot
- [ ] POST /api/auth/password/reset
- [ ] POST /api/auth/mfa/enroll
- [ ] POST /api/auth/mfa/verify
- [ ] POST /api/auth/mfa/challenge
- [ ] POST /api/auth/mfa/challenge/verify

### Organization and Company
- [ ] POST /api/onboarding/complete
- [ ] GET /api/onboarding/company-types
- [ ] GET /api/company/profile
- [ ] PATCH /api/company/profile
- [ ] GET /api/company/modules
- [ ] PATCH /api/company/modules

### User Profile and Preferences
- [ ] GET /api/users/me/profile
- [ ] PATCH /api/users/me/profile
- [ ] GET /api/users/me/preferences
- [ ] PATCH /api/users/me/preferences
- [ ] GET /api/users/me/notifications
- [ ] PATCH /api/users/me/notifications

### Roles and Permissions
- [ ] GET /api/roles
- [ ] POST /api/roles
- [ ] GET /api/roles/{role_id}
- [ ] PATCH /api/roles/{role_id}
- [ ] DELETE /api/roles/{role_id}
- [ ] GET /api/permissions/catalog
- [ ] GET /api/tenant-users
- [ ] POST /api/tenant-users
- [ ] GET /api/admin/permissions-preview

### Subscription and Billing
- [ ] GET /api/subscription
- [ ] PATCH /api/subscription
- [ ] GET /api/subscription/plans
- [ ] GET /api/billing/method
- [ ] PATCH /api/billing/method
- [ ] GET /api/billing/invoices
- [ ] GET /api/billing/invoices/{invoice_id}

### Integrations and Audit
- [ ] GET /api/integrations
- [ ] POST /api/integrations/{provider}/connect
- [ ] POST /api/integrations/{provider}/disconnect
- [ ] GET /api/audit-logs

## Frontend Route Checklist

### Auth and Access
- [x] /login
- [x] /register
- [ ] /verify-email
- [ ] /forgot-password
- [ ] /reset-password
- [ ] /mfa/setup
- [ ] /mfa/challenge

### Organization and Profiles
- [x] /onboarding
- [x] /settings/company
- [ ] /settings/company/modules
- [ ] /settings/profile

### Preferences
- [ ] /settings/language
- [ ] /settings/notifications
- [ ] /settings/notifications/rules
- [ ] /settings/notifications/digest

### Roles and Permissions
- [ ] /settings/roles
- [ ] /settings/roles/new
- [ ] /settings/roles/{role_id}
- [x] /settings/users
- [ ] /settings/permissions

### Subscription and Billing
- [ ] /settings/subscription
- [ ] /settings/billing
- [ ] /settings/billing/invoices
- [ ] /settings/billing/invoices/{invoice_id}

### Integrations and Audit
- [ ] /settings/integrations
- [ ] /settings/audit-history

## Data Model and Persistence Checklist
- [x] tenants
- [x] users
- [x] tenant_memberships
- [x] roles
- [x] projects
- [x] audit_logs
- [ ] mfa_factors
- [ ] password_reset_tokens
- [ ] notification_preferences
- [ ] subscriptions
- [ ] billing_profiles
- [ ] invoices
- [ ] integration_connections

## Security and Governance Checklist
- [x] JWT access token and refresh token flow
- [x] Password hashing
- [x] Tenant-aware authorization
- [x] Role-based permission checks
- [ ] MFA step-up enforcement on sensitive actions
- [ ] Password reset token expiration and one-time use
- [ ] Admin audit logging for role, billing, and integration changes

## Testing Checklist

### Backend
- [x] auth lifecycle tests
- [x] project CRUD tests
- [x] tenant isolation tests
- [x] tenant user assignment tests
- [ ] MFA enroll and challenge tests
- [ ] password reset tests
- [ ] subscription and billing endpoint tests
- [ ] integration connection tests

### Frontend
- [x] onboarding wizard tests
- [x] users assignment success and error tests
- [ ] auth reset password UI tests
- [ ] role and permissions UI tests
- [ ] subscription and billing UI tests
- [ ] integrations and audit filter UI tests

## Definition of Done for This Package
- [ ] All checked planned routes and endpoints implemented
- [ ] Localization coverage for all account-management visible text in en and es
- [ ] Docker compose boot includes migration application
- [ ] CI passes backend and frontend test suites
- [ ] No tenant data leakage in API behavior or UI data presentation
