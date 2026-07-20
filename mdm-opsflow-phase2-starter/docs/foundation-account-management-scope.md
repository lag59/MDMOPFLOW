# Foundation and Account Management

Target: 25-35 screens
Planned total: 30 screens

## 1) Authentication and Access (7 screens)
1. Login
2. Register account
3. Verify email
4. MFA setup (choose method)
5. MFA challenge (code entry)
6. Forgot password (request reset)
7. Reset password (new password form)

## 2) Organization and Company Setup (4 screens)
8. Organization setup wizard start
9. Company details (legal name, type, address)
10. Company modules and preferences
11. Setup confirmation and first admin assignment

## 3) User and Account Profiles (4 screens)
12. User profile view
13. User profile edit
14. Company profile view
15. Company profile edit

## 4) Preferences and Notifications (4 screens)
16. Language preference
17. Notification channels (email, push, SMS)
18. Notification rules by event type
19. Digest and quiet-hours settings

## 5) Roles and Permissions (5 screens)
20. Roles list
21. Role details
22. Create or edit role
23. Permission matrix by module
24. User-role assignment by organization

## 6) Subscription and Billing (4 screens)
25. Subscription overview
26. Plan and seat management
27. Billing method and invoices
28. Billing history and receipts

## 7) Integrations and Audit (2 screens)
29. Integrations hub (connected apps and status)
30. Audit history (filters, actor, entity, action)

---

## Data Domains
- Identity: users, credentials, MFA factors, sessions
- Organization: tenant, company profile, org preferences
- Access Control: roles, permissions, assignments
- Communication: notification preferences and delivery events
- Commercial: subscription, plan, seats, invoices, payment method
- Platform: integrations, audit logs

## Suggested Delivery Order
1. Login, registration, password reset
2. Organization setup and company profile
3. User profile and language preference
4. Roles, permissions, and user-role assignment
5. Notification settings
6. Subscription and billing
7. Integrations and audit history
8. MFA enablement and enforcement

## MVP Acceptance Criteria
- Users can register, log in, and reset password
- Tenant organization can be created and configured
- Company and user profile can be updated
- Language preference persists per user
- Notification settings can be saved and read back
- Roles and permissions enforce access boundaries
- Subscription and billing pages show active plan and invoice history
- Integrations list connection status
- Audit history records major admin and security actions
- MFA can be enabled and required for admin-level actions

## Phase Split
- Phase A (Core Access): Screens 1-15
- Phase B (Governance): Screens 16-24
- Phase C (Commercial and Operations): Screens 25-30
