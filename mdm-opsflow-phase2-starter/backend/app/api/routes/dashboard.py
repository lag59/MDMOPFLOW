from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import RequestContext, require_permissions, resolve_tenant_scope
from app.models import Estimate, IntakeItem, Project, Ticket
from app.schemas import DashboardRoleExperienceResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def _map_role_key(context: RequestContext) -> str:
    if context.user.platform_role.value == "platform_super_admin":
        return "administrator"

    role_names = sorted((context.tenant_roles or set()))
    if not role_names:
        return "project_manager"

    role = role_names[0].lower()
    if "owner" in role:
        return "company_owner"
    if "exec" in role:
        return "executive"
    if "estimate" in role:
        return "estimator"
    if "field_supervisor" in role or "field supervisor" in role or "supervisor" in role:
        return "field_supervisor"
    if "dispatch" in role:
        return "dispatcher"
    if "account" in role:
        return "accounting"
    if "payroll" in role:
        return "payroll"
    if "safety" in role:
        return "safety_manager"
    if "fleet" in role:
        return "fleet_manager"
    if "admin" in role:
        return "administrator"
    if "customer" in role:
        return "customer"
    if "vendor" in role:
        return "vendor"
    return "project_manager"


ROLE_EXPERIENCE: dict[str, dict[str, object]] = {
    "estimator": {
        "role_label": "Estimator",
        "kpi_order": ["estimates", "draft_estimates", "awarded_estimates", "intake_pending_review"],
        "modules": [
            {"label": "Takeoff", "href": "/modules/estimator/takeoff"},
            {"label": "Estimate Versions", "href": "/modules/estimator/estimate-versions"},
            {"label": "Bid Pipeline", "href": "/modules/estimator/bid-pipeline"},
            {"label": "Win/Loss", "href": "/modules/estimator/win-loss"},
        ],
        "quick_actions": [
            {"label": "Open estimator workspace", "href": "/estimator"},
            {"label": "Review ticket inputs", "href": "/tickets"},
            {"label": "View projects", "href": "/projects"},
        ],
    },
    "dispatcher": {
        "role_label": "Dispatcher",
        "kpi_order": ["open_tickets", "tickets", "active_projects", "intake_pending_review"],
        "modules": [
            {"label": "Dispatch Board", "href": "/modules/dispatcher/dispatch-board"},
            {"label": "Crew Calendar", "href": "/modules/dispatcher/crew-calendar"},
            {"label": "Route Planning", "href": "/modules/dispatcher/route-planning"},
            {"label": "Utilization", "href": "/modules/dispatcher/utilization"},
        ],
        "quick_actions": [
            {"label": "Assign tickets", "href": "/ticket-manager"},
            {"label": "Review active tickets", "href": "/tickets"},
            {"label": "Open projects", "href": "/projects"},
        ],
    },
    "fleet_manager": {
        "role_label": "Fleet Manager",
        "kpi_order": ["open_tickets", "tickets", "intake_pending_review", "projects"],
        "modules": [
            {"label": "Fleet", "href": "/modules/fleet_manager/fleet"},
            {"label": "Maintenance", "href": "/modules/fleet_manager/maintenance"},
            {"label": "Fuel", "href": "/modules/fleet_manager/fuel"},
            {"label": "Work Orders", "href": "/modules/fleet_manager/work-orders"},
        ],
        "quick_actions": [
            {"label": "Open workspace assets", "href": "/workspace"},
            {"label": "Check dispatch board", "href": "/ticket-manager"},
            {"label": "Inspect tickets", "href": "/tickets"},
        ],
    },
    "safety_manager": {
        "role_label": "Safety Manager",
        "kpi_order": ["intake_pending_review", "intake_items", "open_tickets", "active_projects"],
        "modules": [
            {"label": "Incidents", "href": "/modules/safety_manager/incidents"},
            {"label": "Inspections", "href": "/modules/safety_manager/inspections"},
            {"label": "Toolbox Talks", "href": "/modules/safety_manager/toolbox-talks"},
            {"label": "Corrective Actions", "href": "/modules/safety_manager/corrective-actions"},
        ],
        "quick_actions": [
            {"label": "Open intake queue", "href": "/intake"},
            {"label": "Review extraction issues", "href": "/extraction-queue"},
            {"label": "Open projects", "href": "/projects"},
        ],
    },
    "accounting": {
        "role_label": "Accounting",
        "kpi_order": ["awarded_estimates", "open_tickets", "tickets", "active_projects"],
        "modules": [
            {"label": "AP", "href": "/modules/accounting/ap"},
            {"label": "AR", "href": "/modules/accounting/ar"},
            {"label": "Invoices", "href": "/modules/accounting/invoices"},
            {"label": "Job Cost Ledger", "href": "/modules/accounting/job-cost-ledger"},
        ],
        "quick_actions": [
            {"label": "Open projects", "href": "/projects"},
            {"label": "Review tickets", "href": "/tickets"},
            {"label": "Open estimator", "href": "/estimator"},
        ],
    },
    "executive": {
        "role_label": "Executive",
        "kpi_order": ["active_projects", "projects", "open_tickets", "intake_pending_review"],
        "modules": [
            {"label": "KPI Board", "href": "/modules/executive/kpi-board"},
            {"label": "Revenue", "href": "/modules/executive/revenue"},
            {"label": "Burn Rate", "href": "/modules/executive/burn-rate"},
            {"label": "Risk Radar", "href": "/modules/executive/risk-radar"},
        ],
        "quick_actions": [
            {"label": "Open projects", "href": "/projects"},
            {"label": "Review tickets", "href": "/tickets"},
            {"label": "View all modules", "href": "/modules"},
        ],
    },
    "project_manager": {
        "role_label": "Project Manager",
        "kpi_order": ["active_projects", "open_tickets", "tickets", "intake_pending_review"],
        "modules": [
            {"label": "Projects", "href": "/modules/project_manager/projects"},
            {"label": "Schedule", "href": "/modules/project_manager/schedule"},
            {"label": "RFIs", "href": "/modules/project_manager/rfis"},
            {"label": "Change Orders", "href": "/modules/project_manager/change-orders"},
        ],
        "quick_actions": [
            {"label": "Create project", "href": "/projects/new"},
            {"label": "Open dispatch board", "href": "/ticket-manager"},
            {"label": "Open daily production", "href": "/daily-production"},
        ],
    },
    "company_owner": {
        "role_label": "Company Owner",
        "kpi_order": ["active_projects", "open_tickets", "awarded_estimates", "intake_pending_review"],
        "modules": [
            {"label": "Executive Dashboard", "href": "/modules/company_owner/executive-dashboard"},
            {"label": "Portfolio", "href": "/modules/company_owner/portfolio"},
            {"label": "Forecasting", "href": "/modules/company_owner/forecasting"},
            {"label": "Approvals", "href": "/modules/company_owner/approvals"},
        ],
        "quick_actions": [
            {"label": "Open projects", "href": "/projects"},
            {"label": "Review intake", "href": "/intake"},
            {"label": "View modules", "href": "/modules"},
        ],
    },
    "field_supervisor": {
        "role_label": "Field Supervisor",
        "kpi_order": ["open_tickets", "tickets", "intake_pending_review", "active_projects"],
        "modules": [
            {"label": "Daily Field Reports", "href": "/field-supervisor"},
            {"label": "Safety", "href": "/modules/field_supervisor/safety"},
            {"label": "Production", "href": "/modules/field_supervisor/production"},
            {"label": "Crew", "href": "/modules/field_supervisor/crew"},
        ],
        "quick_actions": [
            {"label": "Submit daily report", "href": "/daily-production"},
            {"label": "Open ticket queue", "href": "/tickets"},
            {"label": "Open projects", "href": "/projects"},
        ],
    },
    "payroll": {
        "role_label": "Payroll",
        "kpi_order": ["active_projects", "tickets", "open_tickets", "intake_items"],
        "modules": [
            {"label": "Timecards", "href": "/modules/payroll/timecards"},
            {"label": "Overtime", "href": "/modules/payroll/overtime"},
            {"label": "Payroll Runs", "href": "/modules/payroll/payroll-runs"},
            {"label": "Labor Cost Allocation", "href": "/modules/payroll/labor-cost-allocation"},
        ],
        "quick_actions": [
            {"label": "Open workspace", "href": "/workspace"},
            {"label": "Review projects", "href": "/projects"},
            {"label": "Open tickets", "href": "/tickets"},
        ],
    },
    "administrator": {
        "role_label": "Administrator",
        "kpi_order": ["projects", "active_projects", "tickets", "intake_pending_review"],
        "modules": [
            {"label": "User Admin", "href": "/modules/administrator/user-admin"},
            {"label": "Role Policies", "href": "/modules/administrator/role-policies"},
            {"label": "Audit Logs", "href": "/modules/administrator/audit-logs"},
            {"label": "Integrations", "href": "/modules/administrator/integrations"},
        ],
        "quick_actions": [
            {"label": "Open user settings", "href": "/settings/users"},
            {"label": "Open platform admin", "href": "/platform-admin"},
            {"label": "View modules", "href": "/modules"},
        ],
    },
    "customer": {
        "role_label": "Customer",
        "kpi_order": ["active_projects", "projects", "tickets", "intake_pending_review"],
        "modules": [
            {"label": "Project Snapshot", "href": "/modules/customer/project-snapshot"},
            {"label": "Milestones", "href": "/modules/customer/milestones"},
            {"label": "Documents", "href": "/modules/customer/documents"},
            {"label": "Billing Status", "href": "/modules/customer/billing-status"},
        ],
        "quick_actions": [
            {"label": "Open projects", "href": "/projects"},
            {"label": "View documents", "href": "/extraction-queue"},
            {"label": "View modules", "href": "/modules"},
        ],
    },
    "vendor": {
        "role_label": "Vendor",
        "kpi_order": ["tickets", "open_tickets", "projects", "intake_pending_review"],
        "modules": [
            {"label": "Purchase Orders", "href": "/modules/vendor/purchase-orders"},
            {"label": "Invoice Submit", "href": "/modules/vendor/invoice-submit"},
            {"label": "Delivery Tracking", "href": "/modules/vendor/delivery-tracking"},
            {"label": "Compliance Docs", "href": "/modules/vendor/compliance-docs"},
        ],
        "quick_actions": [
            {"label": "Open vendor workspace", "href": "/vendor"},
            {"label": "Review projects", "href": "/projects"},
            {"label": "View modules", "href": "/modules"},
        ],
    },
}


def _build_alerts(*, role_key: str, active_projects: int, open_tickets: int, draft_estimates: int, intake_pending_review: int, awarded_estimates: int) -> list[str]:
    alerts: list[str] = []
    if intake_pending_review > 0:
        alerts.append(f"{intake_pending_review} intake items require review.")
    if open_tickets > 0:
        alerts.append(f"{open_tickets} tickets remain open.")
    if role_key in {"estimator", "executive", "company_owner"} and draft_estimates > 0:
        alerts.append(f"{draft_estimates} estimates are still in draft.")
    if role_key in {"dispatcher", "fleet_manager"} and active_projects > 0 and open_tickets > active_projects * 3:
        alerts.append("Dispatch load is high relative to active projects.")
    if role_key in {"accounting", "executive", "company_owner"} and awarded_estimates > 0 and open_tickets > 0:
        alerts.append("Awarded estimates and open tickets indicate pending billing follow-through.")
    return alerts[:3]


@router.get(
    "/role-experience",
    response_model=DashboardRoleExperienceResponse,
    operation_id="dashboard_role_experience",
    summary="Get role-aware dashboard experience",
)
def get_role_experience(
    context: RequestContext = Depends(require_permissions("project_read")),
    db: Session = Depends(get_db),
):
    tenant_id = resolve_tenant_scope(context)
    role_key = _map_role_key(context)
    profile = ROLE_EXPERIENCE.get(role_key, ROLE_EXPERIENCE["project_manager"])

    projects = db.scalars(select(Project).where(Project.tenant_id == tenant_id)).all()
    tickets = db.scalars(select(Ticket).where(Ticket.tenant_id == tenant_id)).all()
    estimates = db.scalars(select(Estimate).where(Estimate.tenant_id == tenant_id)).all()
    intake_items = db.scalars(select(IntakeItem).where(IntakeItem.tenant_id == tenant_id)).all()

    active_projects = sum(1 for item in projects if item.status and item.status.value == "active")
    open_tickets = sum(1 for item in tickets if (item.status or "") != "closed")
    draft_estimates = sum(1 for item in estimates if (item.status or "") == "Draft Estimate")
    awarded_estimates = sum(1 for item in estimates if (item.status or "") in {"Awarded", "Converted to Project"})
    intake_pending_review = sum(1 for item in intake_items if getattr(item, "status", None) == "pending_review")

    alerts = _build_alerts(
        role_key=role_key,
        active_projects=active_projects,
        open_tickets=open_tickets,
        draft_estimates=draft_estimates,
        intake_pending_review=intake_pending_review,
        awarded_estimates=awarded_estimates,
    )

    return DashboardRoleExperienceResponse(
        role_key=role_key,
        role_label=str(profile["role_label"]),
        kpi_order=[str(item) for item in profile["kpi_order"]],
        modules=[dict(item) for item in profile["modules"]],
        quick_actions=[dict(item) for item in profile["quick_actions"]],
        alerts=alerts,
    )
