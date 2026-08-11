ROLE_PERMISSIONS = {
    "platform_super_admin": ["*"],
    "tenant_admin": [
        "project_read",
        "project_write",
        "project_approve",
        "intake_read",
        "intake_write",
        "intake_review",
        "estimate_read",
        "estimate_write",
        "dispatch_read",
        "dispatch_write",
        "finance_read",
        "finance_write",
        "finance_approve",
        "payroll_read",
        "payroll_write",
        "safety_read",
        "safety_write",
        "fleet_read",
        "fleet_write",
        "admin_read",
        "admin_write",
        "billing_read",
        "billing_write",
        "ai_assignment_read",
        "ai_assignment_write",
        "extraction_read",
        "extraction_review",
        "extraction_approve",
    ],
    "owner": [
        "project_read",
        "project_write",
        "project_approve",
        "intake_read",
        "intake_write",
        "intake_review",
        "estimate_read",
        "finance_read",
        "finance_approve",
        "payroll_read",
        "safety_read",
        "fleet_read",
        "admin_read",
        "billing_read",
        "billing_write",
        "ai_assignment_read",
        "ai_assignment_write",
        "extraction_read",
        "extraction_review",
        "extraction_approve",
    ],
    "executive": [
        "project_read",
        "intake_read",
        "estimate_read",
        "finance_read",
        "payroll_read",
        "safety_read",
        "fleet_read",
        "billing_read",
        "ai_assignment_read",
        "extraction_read",
    ],
    "project_manager": [
        "project_read",
        "project_write",
        "intake_read",
        "intake_write",
        "intake_review",
        "estimate_read",
        "estimate_write",
        "dispatch_read",
        "dispatch_write",
        "safety_read",
        "safety_write",
        "admin_read",
        "ai_assignment_read",
        "ai_assignment_write",
        "extraction_read",
        "extraction_review",
    ],
    "estimator": ["estimate_read", "estimate_write", "project_read", "intake_read", "intake_review", "extraction_read"],
    "field_supervisor": ["project_read", "intake_read", "intake_write", "safety_read", "safety_write", "dispatch_read", "extraction_read", "admin_read"],
    "dispatcher": ["dispatch_read", "dispatch_write", "project_read", "fleet_read", "intake_read", "extraction_read"],
    "accounting": ["finance_read", "finance_write", "billing_read", "billing_write", "project_read", "estimate_read", "intake_read", "extraction_read"],
    "payroll": ["payroll_read", "payroll_write", "project_read", "intake_read", "extraction_read"],
    "safety_manager": ["safety_read", "safety_write", "project_read", "intake_read"],
    "fleet_manager": ["fleet_read", "fleet_write", "dispatch_read", "dispatch_write", "project_read", "intake_read"],
    "administrator": ["admin_read", "admin_write", "billing_read", "billing_write", "ai_assignment_read", "ai_assignment_write", "project_read", "project_write", "intake_read", "intake_write", "extraction_read", "extraction_review", "extraction_approve"],
    "customer": ["portal_customer_read", "project_read", "intake_read"],
    "vendor": ["portal_vendor_write", "project_read", "intake_read"],
}

ALL_KNOWN_PERMISSIONS = sorted(
    {
        permission
        for permissions in ROLE_PERMISSIONS.values()
        for permission in permissions
        if permission != "*"
    }
)


def resolve_permissions(role_name: str, stored_permissions: str | None = None) -> set[str]:
    base = set(ROLE_PERMISSIONS.get(role_name, []))
    if stored_permissions:
        base.update({item.strip() for item in stored_permissions.split(",") if item.strip()})
    return base


def permissions_csv_for_role(role_name: str) -> str:
    return ",".join(ROLE_PERMISSIONS.get(role_name, []))


def permission_exists(permission: str) -> bool:
    return permission in ALL_KNOWN_PERMISSIONS
