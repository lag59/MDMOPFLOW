# Phase 2 Product Blueprint

## Scope Summary
- Build a reusable, bilingual, AI-native product system for web, mobile, and super-admin surfaces.
- Deliver a validated MVP slice (60-80 screens) first, then scale to the full inventory through templates and component reuse.

## Screen Inventory Targets

### Web application
- Target range: 250-300 screens
- Lower/upper planning range: 230-320 screens

#### Domain ranges
- Foundation and account management: 25-35
- Executive and analytics: 20-30
- Projects and field operations: 35-45
- AI Intake and Document Intelligence: 25-35
- Estimating and bidding: 25-35
- Financial operations: 30-40
- Fleet, equipment, GPS, and dispatch: 30-40
- Safety, training, and compliance: 25-35
- Portals: 15-25

### Mobile application
- Target range: 150-200 screens
- Role-adaptive UI for:
  - drivers
  - operators
  - field employees
  - foremen
  - superintendents
  - safety personnel
  - inspectors
  - managers away from office

### Super-admin application
- Target range: 100-125 screens
- Dedicated platform-owner portal separated from customer admin views.

## Role-Adaptive Mobile Surface

### Shared mobile screens
- login
- language selection
- profile
- notifications
- offline status
- synchronization
- AI assistant
- document scanner
- camera upload
- signature capture
- settings

### Driver experience
- clock in/out
- assigned route
- dispatch details
- GPS trip
- load entry
- ticket scan
- delivery confirmation
- vehicle inspection
- fuel entry
- hours summary
- incident report

### Foreman experience
- crew attendance
- daily plan
- production entry
- equipment assignment
- material request
- ticket approval
- daily report
- toolbox talk
- safety observation
- photo documentation
- time approval

### Superintendent and project manager
- project dashboard
- budget summary
- schedule
- production
- pending approvals
- change orders
- field reports
- AI insights
- issue escalation

### Safety personnel
- inspections
- toolbox talks
- JHAs
- incident reporting
- near misses
- training validation
- certificate scanning
- corrective actions

### Equipment and fleet users
- equipment assignment
- inspection
- maintenance request
- machine hours
- fuel
- GPS
- fault alerts
- rental return

## Super-Admin Experience

### Personas
- Libia A. Gaviria, RN, BSN
- support administrators
- implementation specialists
- AI quality reviewers
- security administrators
- customer-success teams

### Platform management
- tenant list and profile
- user management
- subscriptions and plans
- billing
- feature flags
- trial management
- usage limits and storage
- account suspension
- tenant support access

### AI Operations Center
- AI processing volume
- OCR accuracy
- model performance
- prompt versions
- confidence trends
- extraction failures
- correction queue
- template library
- field-level accuracy
- processing costs
- model routing
- escalation rules
- AI audit logs

### System operations
- platform health
- API performance
- worker queues
- failed jobs
- integrations
- error logs
- security events
- database health
- storage health
- deployment status
- incident management

### Customer success
- onboarding progress
- adoption metrics
- customer health
- support history
- training status
- renewal risk
- feature usage
- customer feedback
- implementation milestones

## Reusable Design System

### Foundations
- color
- typography
- spacing
- grid
- shadows
- borders
- motion
- accessibility
- dark mode
- light mode
- English and Spanish
- responsive behavior

### Core components
- buttons
- inputs
- dropdowns
- date pickers
- tables
- cards
- tabs
- side nav and top nav
- breadcrumbs
- modals
- drawers
- notifications
- filters and search
- file upload
- maps
- charts
- data grids
- approval controls
- signatures
- AI panels
- confidence indicators
- audit timelines

### Construction-specific components
- project status card
- budget health card
- cost-code table
- ticket review panel
- OCR confidence row
- equipment card
- truck card
- dispatch board
- GPS map marker
- certification badge
- compliance alert
- estimate worksheet
- change-order panel
- inspection checklist
- daily report builder

## Core Page Templates (25-35)
- dashboard template
- list template
- record-detail template
- creation wizard
- bulk-upload template
- AI review template
- approval queue
- map and dispatch template
- budget template
- analytics template
- document viewer
- timeline and audit template
- settings template
- portal template
- mobile task template
- mobile scan template
- mobile checklist template
- admin operations template

## Bilingual Requirements
- Design English and Spanish together from day one.
- Every component must support longer Spanish labels and regional terminology.
- Support user-level language preference and company default language.
- Instant language switching is required.
- Mixed-language AI prompts and bilingual reports/notifications are required.
- Layouts must not break from string-length expansion.

## AI Experience Requirements

### Persistent copilot
- Present on all major pages as a standard action surface.
- Example actions:
  - explain budget variance
  - generate invoice from approved tickets
  - find duplicates
  - translate reports
  - find expiring certifications
  - prepare dispatch

### Proactive AI action cards
- Surface problems, recommendations, missing data, predicted overruns, compliance risks, duplicate docs, unusual costs, and overdue approvals.

### AI transparency
- Show source, confidence, reasoning summary, affected records, financial impact, and approval requirement for every recommendation.

## Visual Direction
- modern
- clean
- spacious
- premium
- professional
- calm
- field-friendly
- accessible

### Light mode
- soft off-white background
- white cards
- dark navy text
- restrained orange accents
- blue for AI and analytics

### Dark mode
- deep navy background
- elevated dark panels
- high-contrast data
- subtle blue and orange accents

### Interaction patterns
- minimal clicks
- quick actions
- smart defaults
- inline editing
- autosave
- AI suggestions
- keyboard shortcuts
- responsive tables
- clear empty states
- clear error recovery

## Phase 2 Weekly Plan

### Week 1: Design foundations
- brand application
- light and dark themes
- bilingual typography
- spacing and grid
- icon library
- naming system
- accessibility rules

### Week 2: Core components
- navigation
- forms
- tables
- cards
- charts
- uploads
- AI panels
- maps
- approvals
- audit timelines

### Week 3: Primary web workflows
- onboarding
- dashboard
- projects
- tickets
- AI Intake Hub
- review/approval
- budgets
- analytics

### Week 4: Ops and financial workflows
- estimating
- bids
- contracts
- payroll
- accounting
- purchasing
- QuickBooks sync
- equipment and dispatch

### Week 5: Safety and compliance
- OSHA
- CPR
- certifications
- inspections
- incidents
- toolbox talks
- compliance dashboards

### Week 6: Mobile
- driver
- field employee
- foreman
- superintendent
- safety
- manager
- offline workflows
- GPS
- camera
- signatures

### Week 7: Portals and super-admin
- vendor portal
- customer portal
- employee portal
- platform admin
- AI quality center
- tenant support
- system health

### Week 8: Prototype and validation
- clickable prototype
- bilingual validation
- usability testing
- contractor feedback
- mobile testing
- accessibility review
- design handoff
- component docs

## Deliverables by End of Phase 2
- Figma design system
- bilingual component library
- web prototype
- mobile prototype
- super-admin prototype
- screen inventory
- user-flow diagrams
- responsive rules
- accessibility standards
- developer handoff specs
- design tokens
- reusable component docs
- usability test results
- approved MVP screen set

## MVP First Slice (60-80 screens)
- authentication and onboarding
- executive dashboard
- projects
- tickets
- AI bulk intake
- OCR review
- cost and budget
- estimates
- fleet and equipment
- timekeeping
- safety and certifications
- mobile driver workflow
- mobile foreman workflow
- super-admin AI review center

## Execution Rules
- Build all new screens from templates unless a unique workflow explicitly requires a new layout.
- Define and lock component APIs before high-volume screen production.
- Track each screen with ID, template type, owner role, data dependencies, and acceptance criteria.
- Prioritize workflows that include both UI and AI decision transparency.
