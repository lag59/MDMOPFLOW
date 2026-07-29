import { getAccessToken } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";
import { mapBackendRole, type RoleKey } from "@/lib/roles";

export type RoleAccessContext = {
  roleKey: RoleKey;
  isSuperAdmin: boolean;
};

type MeMembership = {
  role_name: string;
};

type MeResponse = {
  platform_role: string;
  memberships: MeMembership[];
};

export async function getCurrentRoleAccess(): Promise<RoleAccessContext | null> {
  const token = getAccessToken();
  if (!token) {
    return null;
  }

  const response = await fetch(`${getApiBaseUrl()}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    return null;
  }

  const me = (await response.json()) as MeResponse;
  const normalizedPlatformRole = (me.platform_role || "").toLowerCase();
  return {
    roleKey: mapBackendRole(me.platform_role, me.memberships?.[0]?.role_name),
    isSuperAdmin: normalizedPlatformRole === "platform_super_admin",
  };
}

export function canAccessModuleRole(context: RoleAccessContext | null, routeRoleKey: string): boolean {
  if (!context) {
    return false;
  }

  if (context.isSuperAdmin) {
    return true;
  }

  return context.roleKey === routeRoleKey;
}
