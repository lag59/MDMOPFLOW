FORMAL_PERMISSION_CATALOG: dict[str, str] = {
    "project.view": "View project records and project-level metrics.",
    "project.manage": "Create, edit, and delete projects.",
    "project.approve": "Approve project state transitions and approvals.",
    "intake.view": "View intake uploads, queues, and intake history.",
    "intake.manage": "Upload, edit, and resolve intake items.",
    "intake.review": "Review, retry, and replay intake integration events.",
    "estimate.view": "View estimates and estimate history.",
    "estimate.create": "Create new estimates.",
    "estimate.edit": "Edit existing estimates and line items.",
    "dispatch.view": "View dispatch workloads and queue status.",
    "dispatch.manage": "Create/update dispatch assignments.",
    "finance.view": "View finance metrics and summaries.",
    "finance.manage": "Edit finance records and entries.",
    "finance.approve": "Approve finance workflows and records.",
    "payroll.view": "View payroll records.",
    "payroll.process": "Run payroll processing workflows.",
    "safety.view": "View safety records and observations.",
    "safety.manage": "Manage safety records, workflows, and actions.",
    "fleet.view": "View fleet assets and utilization.",
    "fleet.manage": "Manage fleet assets and assignments.",
    "user.view": "View tenant user directory and role assignments.",
    "user.manage": "Manage tenant users and platform access flags.",
    "membership.assign": "Assign roles and memberships to tenant users.",
    "billing.view": "View billing records and invoices.",
    "billing.manage": "Create/update billing records and workflows.",
    "ai.assignment.view": "View AI assignment routing and outputs.",
    "ai.assignment.manage": "Manage AI assignment routing decisions.",
    "extraction.view": "View extraction records and OCR outputs.",
    "extraction.review": "Review extraction issues and quality outcomes.",
    "extraction.approve": "Approve extraction outputs for downstream use.",
    "portal.customer.view": "Access customer portal read views.",
    "portal.vendor.submit": "Submit vendor portal updates and entries.",
}

ROLE_PERMISSION_MATRIX: dict[str, list[str]] = {
    "platform_super_admin": ["*"],
    "tenant_admin": [
        "project.view",
        "project.manage",
        "project.approve",
        "intake.view",
        "intake.manage",
        "intake.review",
        "estimate.view",
        "estimate.create",
        "estimate.edit",
        "dispatch.view",
        "dispatch.manage",
        "finance.view",
        "finance.manage",
        "finance.approve",
        "payroll.view",
        "payroll.process",
        "safety.view",
        "safety.manage",
        "fleet.view",
        "fleet.manage",
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "billing.manage",
        "ai.assignment.view",
        "ai.assignment.manage",
        "extraction.view",
        "extraction.review",
        "extraction.approve",
    ],
    "owner": [
        "project.view",
        "project.manage",
        "project.approve",
        "intake.view",
        "intake.manage",
        "intake.review",
        "estimate.view",
        "finance.view",
        "finance.approve",
        "payroll.view",
        "safety.view",
        "fleet.view",
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "billing.manage",
        "portal.vendor.submit",
        "ai.assignment.view",
        "ai.assignment.manage",
        "extraction.view",
        "extraction.review",
        "extraction.approve",
    ],
    "executive": [
        "project.view",
        "intake.view",
        "estimate.view",
        "finance.view",
        "payroll.view",
        "safety.view",
        "fleet.view",
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "ai.assignment.view",
        "extraction.view",
    ],
    "project_manager": [
        "project.view",
        "project.manage",
        "intake.view",
        "intake.manage",
        "intake.review",
        "estimate.view",
        "estimate.create",
        "estimate.edit",
        "dispatch.view",
        "dispatch.manage",
        "safety.view",
        "safety.manage",
        "user.view",
        "user.manage",
        "membership.assign",
        "portal.vendor.submit",
        "ai.assignment.view",
        "ai.assignment.manage",
        "extraction.view",
        "extraction.review",
    ],
    "estimator": [
        "estimate.view",
        "estimate.create",
        "estimate.edit",
        "project.view",
        "intake.view",
        "intake.review",
        "user.view",
        "user.manage",
        "membership.assign",
        "extraction.view",
    ],
    "field_supervisor": [
        "project.view",
        "project.manage",
        "intake.view",
        "intake.manage",
        "safety.view",
        "safety.manage",
        "dispatch.view",
        "extraction.view",
        "user.view",
    ],
    "dispatcher": [
        "dispatch.view",
        "dispatch.manage",
        "project.view",
        "fleet.view",
        "intake.view",
        "extraction.view",
    ],
    "accounting": [
        "finance.view",
        "finance.manage",
        "billing.view",
        "billing.manage",
        "project.view",
        "estimate.view",
        "intake.view",
        "extraction.view",
    ],
    "payroll": [
        "payroll.view",
        "payroll.process",
        "project.view",
        "intake.view",
        "extraction.view",
    ],
    "safety_manager": [
        "safety.view",
        "safety.manage",
        "project.view",
        "intake.view",
    ],
    "fleet_manager": [
        "fleet.view",
        "fleet.manage",
        "dispatch.view",
        "dispatch.manage",
        "project.view",
        "intake.view",
    ],
    "administrator": [
        "user.view",
        "user.manage",
        "membership.assign",
        "billing.view",
        "billing.manage",
        "ai.assignment.view",
        "ai.assignment.manage",
        "project.view",
        "project.manage",
        "intake.view",
        "intake.manage",
        "extraction.view",
        "extraction.review",
        "extraction.approve",
    ],
    "customer": ["portal.customer.view"],
    "vendor": ["portal.vendor.submit"],
}

ROLE_PERMISSIONS = ROLE_PERMISSION_MATRIX

LEGACY_PERMISSION_REQUIREMENTS: dict[str, set[str]] = {
    "project_read": {"project.view"},
    "project_write": {"project.manage"},
    "project_approve": {"project.approve"},
    "intake_read": {"intake.view"},
    "intake_write": {"intake.manage"},
    "intake_review": {"intake.review"},
    "estimate_read": {"estimate.view"},
    "estimate_write": {"estimate.create", "estimate.edit"},
    "dispatch_read": {"dispatch.view"},
    "dispatch_write": {"dispatch.manage"},
    "finance_read": {"finance.view"},
    "finance_write": {"finance.manage"},
    "finance_approve": {"finance.approve"},
    "payroll_read": {"payroll.view"},
    "payroll_write": {"payroll.process"},
    "safety_read": {"safety.view"},
    "safety_write": {"safety.manage"},
    "fleet_read": {"fleet.view"},
    "fleet_write": {"fleet.manage"},
    "admin_read": {"user.view"},
    "admin_write": {"user.manage", "membership.assign"},
    "billing_read": {"billing.view"},
    "billing_write": {"billing.manage"},
    "ai_assignment_read": {"ai.assignment.view"},
    "ai_assignment_write": {"ai.assignment.manage"},
    "extraction_read": {"extraction.view"},
    "extraction_review": {"extraction.review"},
    "extraction_approve": {"extraction.approve"},
    "portal_customer_read": {"portal.customer.view"},
    "portal_vendor_write": {"portal.vendor.submit"},
}

ALL_KNOWN_PERMISSIONS = sorted(
    set(FORMAL_PERMISSION_CATALOG.keys()).union(LEGACY_PERMISSION_REQUIREMENTS.keys())
)


def _apply_legacy_aliases(granular_permissions: set[str]) -> set[str]:
    effective = set(granular_permissions)
    for legacy_permission, required_granular in LEGACY_PERMISSION_REQUIREMENTS.items():
        if required_granular.issubset(granular_permissions):
            effective.add(legacy_permission)
    return effective


def resolve_permissions(role_name: str, stored_permissions: str | None = None) -> set[str]:
    base = set(ROLE_PERMISSION_MATRIX.get(role_name, []))

    if stored_permissions:
        for item in {entry.strip() for entry in stored_permissions.split(",") if entry.strip()}:
            if item in LEGACY_PERMISSION_REQUIREMENTS:
                base.update(LEGACY_PERMISSION_REQUIREMENTS[item])
            else:
                base.add(item)

    if "*" in base:
        return {"*"}

    return _apply_legacy_aliases(base)


def permissions_csv_for_role(role_name: str) -> str:
    permissions = ROLE_PERMISSION_MATRIX.get(role_name, [])
    return ",".join(permissions)


def permission_exists(permission: str) -> bool:
    return permission in ALL_KNOWN_PERMISSIONS
