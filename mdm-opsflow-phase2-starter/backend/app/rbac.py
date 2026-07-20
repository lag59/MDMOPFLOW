ROLE_PERMISSIONS = {
    "platform_super_admin": ["*"],
    "tenant_admin": [
        "project_read",
        "project_write",
        "project_approve",
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
    ],
    "owner": [
        "project_read",
        "project_write",
        "project_approve",
        "estimate_read",
        "finance_read",
        "finance_approve",
        "payroll_read",
        "safety_read",
        "fleet_read",
        "admin_read",
    ],
    "executive": [
        "project_read",
        "estimate_read",
        "finance_read",
        "payroll_read",
        "safety_read",
        "fleet_read",
    ],
    "project_manager": [
        "project_read",
        "project_write",
        "estimate_read",
        "dispatch_read",
        "dispatch_write",
        "safety_read",
        "safety_write",
    ],
    "estimator": ["estimate_read", "estimate_write", "project_read"],
    "dispatcher": ["dispatch_read", "dispatch_write", "project_read", "fleet_read"],
    "accounting": ["finance_read", "finance_write", "project_read", "estimate_read"],
    "payroll": ["payroll_read", "payroll_write", "project_read"],
    "safety_manager": ["safety_read", "safety_write", "project_read"],
    "fleet_manager": ["fleet_read", "fleet_write", "dispatch_read", "dispatch_write", "project_read"],
    "administrator": ["admin_read", "admin_write", "project_read", "project_write"],
    "customer": ["portal_customer_read", "project_read"],
    "vendor": ["portal_vendor_write", "project_read"],
}


def resolve_permissions(role_name: str, stored_permissions: str | None = None) -> set[str]:
    base = set(ROLE_PERMISSIONS.get(role_name, []))
    if stored_permissions:
        base.update({item.strip() for item in stored_permissions.split(",") if item.strip()})
    return base


def permissions_csv_for_role(role_name: str) -> str:
    return ",".join(ROLE_PERMISSIONS.get(role_name, []))
