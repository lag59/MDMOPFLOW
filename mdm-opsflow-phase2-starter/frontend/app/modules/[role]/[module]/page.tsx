"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useEffect, useMemo, useState } from "react";
import * as XLSX from "xlsx";

import AppShell from "@/components/AppShell";
import { getCustomerPortalBillingStatus, getCustomerPortalDocumentStatus, listCustomerPortalProjects, type CustomerPortalBillingStatus, type CustomerPortalDocumentStatus, type CustomerPortalProjectSummary } from "@/lib/customerPortal";
import { createEstimatorTakeoff, createEstimatorVersion, getEstimatorSummary, listEstimatorBidPipelineItems, listEstimatorTakeoffs, listEstimatorVersions, listEstimatorWinLossRecords, type EstimatorBidPipelineItem, type EstimatorSummary, type EstimatorTakeoff, type EstimatorVersion, type EstimatorWinLossRecord } from "@/lib/estimator";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getModuleDetail } from "@/lib/modules";
import { getPayrollSummary, listPayrollRuns, listPayrollTimecards, type PayrollRun, type PayrollSummary, type PayrollTimecard } from "@/lib/payroll";
import { fetchReplayTokenStateAlerts, type ReplayTokenStateAlerts } from "@/lib/replayTokens";
import { getApiBaseUrl } from "@/lib/i18n";
import { canAccessModuleRole, getCurrentRoleAccess, type RoleAccessContext } from "@/lib/roleAccess";
import { createTicket, listMaterialDensityPresets, listTickets, type MaterialDensityPreset, type Ticket } from "@/lib/tickets";
import { listVendorComplianceDocuments, listVendorDeliveryRecords, listVendorInvoiceSubmissions, listVendorPurchaseOrders, type VendorComplianceDocument, type VendorDeliveryRecord, type VendorInvoiceSubmission, type VendorPurchaseOrder } from "@/lib/vendor";

type Project = {
  id: string;
  project_name: string;
  project_number: string;
  status: string;
};

type WorkspaceResource = {
  id: string;
  name?: string;
  unit_number?: string;
};

type AdminOverview = {
  tenants: number;
  users: number;
  projects: number;
};

type AdminUser = {
  id: string;
  email: string;
  display_name: string;
  title: string;
  platform_role: "platform_super_admin" | "user";
  is_active: boolean;
};

type ServiceInsights = {
  tickets: number;
  intake_items: number;
  intake_needs_review: number;
  extractions_pending_review: number;
  extractions_review_submitted: number;
  unresolved_extraction_issues: number;
  integration_events_pending: number;
  integration_events_failed: number;
  opportunities: string[];
};

type DailyFieldReport = {
  id: string;
  report_number?: string;
  project_id?: string;
  report_date?: string;
  reporting_supervisor?: string;
  status?: string;
  work_performed?: string;
};

type TenantUserMembership = {
  user_id: string;
  email: string;
  display_name: string;
  title: string;
  role_name: string;
  status: string;
};

type ProjectProfitability = {
  project_id: string;
  project_name: string;
  status: string;
  actual_revenue: number;
  actual_cost: number;
  gross_profit: number;
  profit_margin: number;
  cost_overrun: boolean;
  revenue_shortfall: boolean;
  ticket_count: number;
};

type BridgeWorkspaceDraft = {
  initiative: string;
  portfolioView: string;
  riskLevel: "low" | "medium" | "high";
  marginTarget: string;
  owner: string;
  dueDate: string;
  linkedProjectId: string;
  notes: string;
};

type EstimateCrewLine = {
  id: string;
  crewType: string;
  headcount: number;
  hourlyRate: number;
  hours: number;
};

type EstimateMachineLine = {
  id: string;
  machineType: string;
  count: number;
  hourlyRate: number;
  hours: number;
};

type EstimateMaterialLine = {
  id: string;
  materialName: string;
  quantity: number;
  unit: string;
  unitCost: number;
};

type ProjectManagerLocale = "en" | "es";

type ProjectManagerActionDraft = {
  title: string;
  projectId: string;
  category: string;
  priority: string;
  riskLevel: string;
  responsiblePerson: string;
  dueDate: string;
  description: string;
  status: string;
  notes: string;
};

const DEFAULT_BRIDGE_DRAFT: BridgeWorkspaceDraft = {
  initiative: "",
  portfolioView: "",
  riskLevel: "medium",
  marginTarget: "",
  owner: "",
  dueDate: "",
  linkedProjectId: "",
  notes: "",
};

const DEFAULT_CREW_LINES: EstimateCrewLine[] = [
  { id: "crew-1", crewType: "Foreman", headcount: 1, hourlyRate: 68, hours: 8 },
  { id: "crew-2", crewType: "Operator", headcount: 2, hourlyRate: 52, hours: 8 },
  { id: "crew-3", crewType: "Laborer", headcount: 2, hourlyRate: 39, hours: 8 },
];

const DEFAULT_MACHINE_LINES: EstimateMachineLine[] = [
  { id: "machine-1", machineType: "Excavator", count: 1, hourlyRate: 165, hours: 8 },
  { id: "machine-2", machineType: "Dump Truck", count: 2, hourlyRate: 125, hours: 8 },
];

const DEFAULT_MATERIAL_LINES: EstimateMaterialLine[] = [
  { id: "material-1", materialName: "Aggregate Base", quantity: 100, unit: "tons", unitCost: 28 },
];

const PROJECT_MANAGER_LABELS: Record<ProjectManagerLocale, Record<string, string>> = {
  en: {
    projectManager: "Project Manager",
    portfolioSummary: "Portfolio Summary",
    activeProjects: "Active Projects",
    projectsAtRisk: "Projects at Risk",
    dailyReportsDue: "Daily Reports Due",
    reportsAwaitingApproval: "Reports Awaiting Approval",
    openActionTickets: "Open Action Tickets",
    unassignedDispatchItems: "Unassigned Dispatch Items",
    potentialChangeOrders: "Potential Change Orders",
    approvalBacklog: "Approval Backlog",
    projectPortfolioView: "Project Portfolio View",
    projectsNeedingAttention: "Projects Needing Attention",
    dailyProductionReview: "Daily Production Review",
    productionPerformance: "Production Performance",
    laborHours: "Labor Hours",
    machineHours: "Machine Hours",
    materialUsage: "Material Usage",
    schedulePressure: "Schedule Pressure",
    executionLoad: "Execution Load",
    actionPlan: "Project Manager Action Plan",
    marginControl: "Margin and Cost Control",
    aiAssist: "AI Project Manager Assist",
    createProject: "Create Project",
    openDailyProduction: "Open Daily Production",
    reviewApprovals: "Review Approvals",
    createActionTicket: "Create Action Ticket",
    runAiReview: "Run AI Project Review",
    exportPdf: "Export PDF",
    exportExcel: "Export Excel",
    switchLanguage: "Switch Language",
    backToModules: "Back to Modules",
    logout: "Logout",
    saveAction: "Save Action",
    assignAction: "Assign Action",
    escalate: "Escalate",
    markResolved: "Mark Resolved",
    createFollowUp: "Create Follow-Up",
    runAiAssist: "Run AI Assist",
  },
  es: {
    projectManager: "Gerente de Proyecto",
    portfolioSummary: "Resumen del Portafolio",
    activeProjects: "Proyectos Activos",
    projectsAtRisk: "Proyectos en Riesgo",
    dailyReportsDue: "Reportes Diarios Pendientes",
    reportsAwaitingApproval: "Reportes por Aprobar",
    openActionTickets: "Tickets de Acción Abiertos",
    unassignedDispatchItems: "Elementos sin Asignar en Despacho",
    potentialChangeOrders: "Órdenes de Cambio Potenciales",
    approvalBacklog: "Aprobaciones Pendientes",
    projectPortfolioView: "Vista de Portafolio de Proyectos",
    projectsNeedingAttention: "Proyectos que Requieren Atención",
    dailyProductionReview: "Revisión de Producción Diaria",
    productionPerformance: "Rendimiento de Producción",
    laborHours: "Horas de Trabajo",
    machineHours: "Horas de Equipo",
    materialUsage: "Uso de Materiales",
    schedulePressure: "Riesgo del Cronograma",
    executionLoad: "Carga de Ejecución",
    actionPlan: "Plan de Acción del Gerente de Proyecto",
    marginControl: "Control de Margen y Costos",
    aiAssist: "Asistente de IA para Gerente de Proyecto",
    createProject: "Crear Proyecto",
    openDailyProduction: "Abrir Producción Diaria",
    reviewApprovals: "Revisar Aprobaciones",
    createActionTicket: "Crear Ticket de Acción",
    runAiReview: "Ejecutar Revisión con IA",
    exportPdf: "Exportar PDF",
    exportExcel: "Exportar Excel",
    switchLanguage: "Cambiar Idioma",
    backToModules: "Volver a Módulos",
    logout: "Cerrar Sesión",
    saveAction: "Guardar Acción",
    assignAction: "Asignar Acción",
    escalate: "Escalar",
    markResolved: "Marcar Resuelta",
    createFollowUp: "Crear Seguimiento",
    runAiAssist: "Ejecutar Asistencia IA",
  },
};

export default function ModuleDetailPage() {
  const params = useParams();
  const role = String(params?.role || "");
  const moduleSlug = String(params?.module || "");
  const detail = getModuleDetail(role, moduleSlug);
  const [projects, setProjects] = useState<Project[]>([]);
  const [profitability, setProfitability] = useState<Map<string, ProjectProfitability>>(new Map());
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [alerts, setAlerts] = useState<ReplayTokenStateAlerts | null>(null);
  const [equipment, setEquipment] = useState<WorkspaceResource[]>([]);
  const [trucks, setTrucks] = useState<WorkspaceResource[]>([]);
  const [employees, setEmployees] = useState<WorkspaceResource[]>([]);
  const [payrollSummary, setPayrollSummary] = useState<PayrollSummary | null>(null);
  const [payrollTimecards, setPayrollTimecards] = useState<PayrollTimecard[]>([]);
  const [payrollRuns, setPayrollRuns] = useState<PayrollRun[]>([]);
  const [adminOverview, setAdminOverview] = useState<AdminOverview | null>(null);
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([]);
  const [serviceInsights, setServiceInsights] = useState<ServiceInsights | null>(null);
  const [dailyReports, setDailyReports] = useState<DailyFieldReport[]>([]);
  const [tenantUsers, setTenantUsers] = useState<TenantUserMembership[]>([]);
  const [permissionCatalog, setPermissionCatalog] = useState<string[]>([]);
  const [materialPresets, setMaterialPresets] = useState<MaterialDensityPreset[]>([]);
  const [customerPortalProjects, setCustomerPortalProjects] = useState<CustomerPortalProjectSummary[]>([]);
  const [customerPortalBilling, setCustomerPortalBilling] = useState<CustomerPortalBillingStatus[]>([]);
  const [customerPortalDocuments, setCustomerPortalDocuments] = useState<CustomerPortalDocumentStatus[]>([]);
  const [vendorPurchaseOrders, setVendorPurchaseOrders] = useState<VendorPurchaseOrder[]>([]);
  const [vendorInvoiceSubmissions, setVendorInvoiceSubmissions] = useState<VendorInvoiceSubmission[]>([]);
  const [vendorDeliveryRecords, setVendorDeliveryRecords] = useState<VendorDeliveryRecord[]>([]);
  const [vendorComplianceDocuments, setVendorComplianceDocuments] = useState<VendorComplianceDocument[]>([]);
  const [estimatorTakeoffs, setEstimatorTakeoffs] = useState<EstimatorTakeoff[]>([]);
  const [estimatorVersions, setEstimatorVersions] = useState<EstimatorVersion[]>([]);
  const [estimatorBidPipelineItems, setEstimatorBidPipelineItems] = useState<EstimatorBidPipelineItem[]>([]);
  const [estimatorWinLossRecords, setEstimatorWinLossRecords] = useState<EstimatorWinLossRecord[]>([]);
  const [estimatorSummary, setEstimatorSummary] = useState<EstimatorSummary | null>(null);
  const [roleAccess, setRoleAccess] = useState<RoleAccessContext | null>(null);
  const [roleAccessResolved, setRoleAccessResolved] = useState(false);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [bridgeDraft, setBridgeDraft] = useState<BridgeWorkspaceDraft>(DEFAULT_BRIDGE_DRAFT);
  const [bridgeDraftMessage, setBridgeDraftMessage] = useState("");
  const [bridgeAiMessage, setBridgeAiMessage] = useState("");
  const [bridgeActionMessage, setBridgeActionMessage] = useState("");
  const [bridgeActionSaving, setBridgeActionSaving] = useState(false);
  const [estimateProjectId, setEstimateProjectId] = useState("");
  const [estimateTicketId, setEstimateTicketId] = useState("");
  const [estimateName, setEstimateName] = useState("Field Production Estimate");
  const [estimateScope, setEstimateScope] = useState("");
  const [contingencyPercent, setContingencyPercent] = useState(8);
  const [markupPercent, setMarkupPercent] = useState(12);
  const [crewLines, setCrewLines] = useState<EstimateCrewLine[]>(DEFAULT_CREW_LINES);
  const [machineLines, setMachineLines] = useState<EstimateMachineLine[]>(DEFAULT_MACHINE_LINES);
  const [materialLines, setMaterialLines] = useState<EstimateMaterialLine[]>(DEFAULT_MATERIAL_LINES);
  const [estimateMessage, setEstimateMessage] = useState("");
  const [estimateSaving, setEstimateSaving] = useState(false);
  const [projectManagerLocale, setProjectManagerLocale] = useState<ProjectManagerLocale>("en");
  const [projectManagerAiMessage, setProjectManagerAiMessage] = useState("");
  const [projectManagerActionMessage, setProjectManagerActionMessage] = useState("");
  const [projectManagerActionSaving, setProjectManagerActionSaving] = useState(false);
  const [projectManagerAiRunning, setProjectManagerAiRunning] = useState(false);
  const [projectManagerExportMessage, setProjectManagerExportMessage] = useState("");
  const [projectManagerExportingPdf, setProjectManagerExportingPdf] = useState(false);
  const [projectManagerExportingExcel, setProjectManagerExportingExcel] = useState(false);
  const [projectManagerActionDraft, setProjectManagerActionDraft] = useState<ProjectManagerActionDraft>({
    title: "",
    projectId: "",
    category: "Production",
    priority: "Medium",
    riskLevel: "Medium",
    responsiblePerson: "",
    dueDate: "",
    description: "",
    status: "Open",
    notes: "",
  });

  const bridgeStorageKey = useMemo(() => {
    if (!detail || detail.route.status !== "bridge") {
      return null;
    }
    const tenantId = getTenantId() || "no-tenant";
    return `opsflow_bridge_${tenantId}_${detail.roleKey}_${detail.moduleSlug}`;
  }, [detail]);

  useEffect(() => {
    if (!bridgeStorageKey || typeof window === "undefined") {
      setBridgeDraft(DEFAULT_BRIDGE_DRAFT);
      setBridgeDraftMessage("");
      return;
    }

    try {
      const raw = window.localStorage.getItem(bridgeStorageKey);
      if (!raw) {
        setBridgeDraft(DEFAULT_BRIDGE_DRAFT);
        setBridgeDraftMessage("No saved bridge draft yet.");
        return;
      }

      const parsed = JSON.parse(raw) as Partial<BridgeWorkspaceDraft>;
      setBridgeDraft({ ...DEFAULT_BRIDGE_DRAFT, ...parsed });
      setBridgeDraftMessage("Bridge draft loaded.");
    } catch {
      setBridgeDraft(DEFAULT_BRIDGE_DRAFT);
      setBridgeDraftMessage("Saved bridge draft could not be read. Starting fresh.");
    }
  }, [bridgeStorageKey]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const saved = window.localStorage.getItem("opsflow_locale");
    if (saved === "es" || saved === "en") {
      setProjectManagerLocale(saved);
    }
  }, []);

  const saveBridgeDraft = () => {
    if (!bridgeStorageKey || typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(bridgeStorageKey, JSON.stringify(bridgeDraft));
    setBridgeDraftMessage("Bridge workspace saved.");
  };

  const resetBridgeDraft = () => {
    if (!bridgeStorageKey || typeof window === "undefined") {
      return;
    }

    window.localStorage.removeItem(bridgeStorageKey);
    setBridgeDraft(DEFAULT_BRIDGE_DRAFT);
    setBridgeDraftMessage("Bridge workspace reset.");
  };

  const runBridgeAiAssist = async () => {
    setBridgeAiMessage("");
    const token = getAccessToken();
    if (!token) {
      setBridgeAiMessage("Login required.");
      return;
    }

    const note = [
      `Bridge workspace: ${detail?.moduleLabel || "module"}`,
      `Initiative: ${bridgeDraft.initiative || "n/a"}`,
      `Scope: ${bridgeDraft.portfolioView || "n/a"}`,
      `Risk: ${bridgeDraft.riskLevel}`,
      `Margin target: ${bridgeDraft.marginTarget || "n/a"}`,
      `Owner: ${bridgeDraft.owner || "n/a"}`,
      `Due: ${bridgeDraft.dueDate || "n/a"}`,
      `Notes: ${bridgeDraft.notes || "n/a"}`,
    ].join("\n");

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/ai/workflow/route`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-ID": getTenantId(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          note,
          company_name: detail?.moduleLabel || "Bridge Workspace",
          reporting_supervisor: bridgeDraft.owner || "Operations",
          material_name: bridgeDraft.portfolioView || "Bridge",
          project_id: bridgeDraft.linkedProjectId || null,
        }),
      });

      if (!response.ok) {
        setBridgeAiMessage("AI assist could not be completed.");
        return;
      }

      const data = (await response.json()) as { routed?: boolean; message?: string };
      setBridgeAiMessage(data.message || "Bridge action routed for follow-up.");
    } catch {
      setBridgeAiMessage("AI assist could not be completed.");
    }
  };

  const createBridgeActionTicket = async () => {
    setBridgeActionMessage("");
    setBridgeActionSaving(true);

    try {
      const created = await createTicket({
        project_id: bridgeDraft.linkedProjectId || null,
        ticket_number: `BRG-${Date.now().toString().slice(-6)}`,
        material: bridgeDraft.initiative || detail?.moduleLabel || "Bridge Initiative",
        origin: "Bridge Module",
        destination: "Operations Queue",
        status: "draft",
        notes: [
          `Module: ${detail?.moduleLabel || "Bridge"}`,
          `Initiative: ${bridgeDraft.initiative || "n/a"}`,
          `Scope: ${bridgeDraft.portfolioView || "n/a"}`,
          `Risk: ${bridgeDraft.riskLevel}`,
          `Margin target: ${bridgeDraft.marginTarget || "n/a"}`,
          `Owner: ${bridgeDraft.owner || "n/a"}`,
          `Due: ${bridgeDraft.dueDate || "n/a"}`,
        ].join("\n"),
      });
      setBridgeActionMessage(`Bridge action ticket created: ${created.ticket_number || created.id}`);
    } catch {
      setBridgeActionMessage("Unable to create bridge action ticket right now.");
    } finally {
      setBridgeActionSaving(false);
    }
  };

  useEffect(() => {
    const resolveRoleAccess = async () => {
      const context = await getCurrentRoleAccess();
      setRoleAccess(context);
      setRoleAccessResolved(true);
    };

    resolveRoleAccess();
  }, []);

  useEffect(() => {
    if (!roleAccessResolved) {
      return;
    }

    if (!detail || !["company_owner", "executive", "project_manager", "estimator", "dispatcher", "accounting", "payroll", "fleet_manager", "safety_manager", "administrator", "customer", "vendor"].includes(detail.roleKey)) {
      return;
    }

    if (!canAccessModuleRole(roleAccess, detail.roleKey)) {
      return;
    }

    const token = getAccessToken();
    if (!token) {
      return;
    }

    const headers = {
      Authorization: `Bearer ${token}`,
      "X-Tenant-ID": getTenantId(),
    };

    const loadInsights = async () => {
      setInsightsLoading(true);
      try {
        const projectRes = await fetch(`${getApiBaseUrl()}/api/projects`, { headers });
        const projectData = (projectRes.ok ? await projectRes.json() : []) as Project[];
        setProjects(projectData);

        const profitEntries = await Promise.all(
          projectData.map(async (project) => {
            try {
              const response = await fetch(`${getApiBaseUrl()}/api/projects/${project.id}/profitability`, { headers });
              if (!response.ok) {
                return null;
              }
              const data = (await response.json()) as ProjectProfitability;
              return [project.id, data] as const;
            } catch {
              return null;
            }
          })
        );

        setProfitability(new Map(profitEntries.filter((entry): entry is readonly [string, ProjectProfitability] => entry !== null)));

        try {
          const [ticketData, alertData, equipmentData, truckData, employeeData, tenantUserData, permissionCatalogData, overviewData, adminUserData, serviceInsightsData, dailyFieldReportData, materialPresetData, payrollSummaryData, payrollTimecardData, payrollRunData, vendorPurchaseOrderData, vendorInvoiceSubmissionData, vendorDeliveryRecordData, vendorComplianceDocumentData, customerPortalProjectData, estimatorTakeoffData, estimatorVersionData, estimatorBidPipelineData, estimatorWinLossData, estimatorSummaryData] = await Promise.all([
            listTickets(),
            fetchReplayTokenStateAlerts({ staleThresholdMinutes: 60, staleActiveThresholdCount: 10 }),
            fetch(`${getApiBaseUrl()}/api/equipment`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/trucks`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/employees`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/tenant-users`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/tenant-users/permissions/catalog`, { headers }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/admin/overview`, { headers: { Authorization: `Bearer ${token}` } }).then((res) => (res.ok ? res.json() : null)),
            fetch(`${getApiBaseUrl()}/api/admin/users`, { headers: { Authorization: `Bearer ${token}` } }).then((res) => (res.ok ? res.json() : [])),
            fetch(`${getApiBaseUrl()}/api/admin/service-insights`, { headers: { Authorization: `Bearer ${token}` } }).then((res) => (res.ok ? res.json() : null)),
            fetch(`${getApiBaseUrl()}/api/daily-field-reports`, { headers }).then((res) => (res.ok ? res.json() : [])),
            listMaterialDensityPresets().catch(() => []),
            getPayrollSummary().catch(() => null),
            listPayrollTimecards().catch(() => []),
            listPayrollRuns().catch(() => []),
            listVendorPurchaseOrders().catch(() => []),
            listVendorInvoiceSubmissions().catch(() => []),
            listVendorDeliveryRecords().catch(() => []),
            listVendorComplianceDocuments().catch(() => []),
            listCustomerPortalProjects().catch(() => []),
            listEstimatorTakeoffs().catch(() => []),
            listEstimatorVersions().catch(() => []),
            listEstimatorBidPipelineItems().catch(() => []),
            listEstimatorWinLossRecords().catch(() => []),
            getEstimatorSummary().catch(() => null),
          ]);
          setTickets(ticketData);
          setAlerts(alertData);
          setEquipment(equipmentData as WorkspaceResource[]);
          setTrucks(truckData as WorkspaceResource[]);
          setEmployees(employeeData as WorkspaceResource[]);
          setTenantUsers(tenantUserData as TenantUserMembership[]);
          setPermissionCatalog(permissionCatalogData as string[]);
          setAdminOverview(overviewData as AdminOverview | null);
          setAdminUsers(adminUserData as AdminUser[]);
          setServiceInsights(serviceInsightsData as ServiceInsights | null);
          setDailyReports(dailyFieldReportData as DailyFieldReport[]);
          setMaterialPresets(materialPresetData as MaterialDensityPreset[]);
          setPayrollSummary(payrollSummaryData as PayrollSummary | null);
          setPayrollTimecards(payrollTimecardData as PayrollTimecard[]);
          setPayrollRuns(payrollRunData as PayrollRun[]);
          setVendorPurchaseOrders(vendorPurchaseOrderData as VendorPurchaseOrder[]);
          setVendorInvoiceSubmissions(vendorInvoiceSubmissionData as VendorInvoiceSubmission[]);
          setVendorDeliveryRecords(vendorDeliveryRecordData as VendorDeliveryRecord[]);
          setVendorComplianceDocuments(vendorComplianceDocumentData as VendorComplianceDocument[]);
          setCustomerPortalProjects(customerPortalProjectData as CustomerPortalProjectSummary[]);
          setEstimatorTakeoffs(estimatorTakeoffData as EstimatorTakeoff[]);
          setEstimatorVersions(estimatorVersionData as EstimatorVersion[]);
          setEstimatorBidPipelineItems(estimatorBidPipelineData as EstimatorBidPipelineItem[]);
          setEstimatorWinLossRecords(estimatorWinLossData as EstimatorWinLossRecord[]);
          setEstimatorSummary(estimatorSummaryData as EstimatorSummary | null);
          const portalProjects = customerPortalProjectData as CustomerPortalProjectSummary[];
          const billingRecords = await Promise.all(
            portalProjects.map((project) => getCustomerPortalBillingStatus(project.project_id).catch(() => null))
          );
          const documentRecords = await Promise.all(
            portalProjects.map((project) => getCustomerPortalDocumentStatus(project.project_id).catch(() => null))
          );
          setCustomerPortalBilling(billingRecords.filter((item): item is CustomerPortalBillingStatus => item !== null));
          setCustomerPortalDocuments(documentRecords.filter((item): item is CustomerPortalDocumentStatus => item !== null));
        } catch {
          setTickets([]);
          setAlerts(null);
          setEquipment([]);
          setTrucks([]);
          setEmployees([]);
          setTenantUsers([]);
          setPermissionCatalog([]);
          setAdminOverview(null);
          setAdminUsers([]);
          setServiceInsights(null);
          setDailyReports([]);
          setMaterialPresets([]);
          setPayrollSummary(null);
          setPayrollTimecards([]);
          setPayrollRuns([]);
          setVendorPurchaseOrders([]);
          setVendorInvoiceSubmissions([]);
          setVendorDeliveryRecords([]);
          setVendorComplianceDocuments([]);
          setCustomerPortalProjects([]);
          setCustomerPortalBilling([]);
          setCustomerPortalDocuments([]);
          setEstimatorTakeoffs([]);
          setEstimatorVersions([]);
          setEstimatorBidPipelineItems([]);
          setEstimatorWinLossRecords([]);
          setEstimatorSummary(null);
        }
      } finally {
        setInsightsLoading(false);
      }
    };

    loadInsights();
  }, [detail?.moduleSlug, detail?.roleKey, roleAccessResolved, roleAccess]);

  const ownerSummary = useMemo(() => {
    const profitabilityItems = Array.from(profitability.values());
    const activeProjects = projects.filter((project) => project.status === "active").length;
    const atRiskProjects = profitabilityItems.filter((item) => item.cost_overrun || item.revenue_shortfall);
    const totalRevenue = profitabilityItems.reduce((acc, item) => acc + Number(item.actual_revenue || 0), 0);
    const totalMargin = profitabilityItems.reduce((acc, item) => acc + Number(item.gross_profit || 0), 0);
    const assignedTickets = tickets.filter((ticket) => !!ticket.project_id).length;

    return {
      activeProjects,
      atRiskProjects,
      totalRevenue,
      totalMargin,
      assignedTickets,
      flaggedApprovals: alerts?.active_tokens_older_than_threshold ?? 0,
      approvalPressure: alerts?.active_tokens_older_than_threshold_exceeded ?? false,
      topAtRiskProjects: atRiskProjects.slice(0, 5),
      unassignedTickets: tickets.filter((ticket) => !ticket.project_id).slice(0, 5),
    };
  }, [alerts, profitability, projects, tickets]);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === estimateProjectId) || null,
    [projects, estimateProjectId]
  );

  const selectedTicket = useMemo(
    () => tickets.find((ticket) => ticket.id === estimateTicketId) || null,
    [tickets, estimateTicketId]
  );

  const selectedProjectProfitability = useMemo(() => {
    if (!selectedProject) {
      return null;
    }
    return profitability.get(selectedProject.id) || null;
  }, [profitability, selectedProject]);

  const crewCost = useMemo(
    () => crewLines.reduce((sum, line) => sum + line.headcount * line.hourlyRate * line.hours, 0),
    [crewLines]
  );

  const machineCost = useMemo(
    () => machineLines.reduce((sum, line) => sum + line.count * line.hourlyRate * line.hours, 0),
    [machineLines]
  );

  const materialCost = useMemo(
    () => materialLines.reduce((sum, line) => sum + line.quantity * line.unitCost, 0),
    [materialLines]
  );

  const estimateBaseCost = crewCost + machineCost + materialCost;
  const estimateContingency = estimateBaseCost * (contingencyPercent / 100);
  const estimateSubtotal = estimateBaseCost + estimateContingency;
  const estimateMarkup = estimateSubtotal * (markupPercent / 100);
  const estimateGrandTotal = estimateSubtotal + estimateMarkup;

  const recommendedCrewHeadcount = useMemo(() => {
    const projectTicketCount = selectedProjectProfitability?.ticket_count || 0;
    const ticketTons = Number(selectedTicket?.tons || 0);
    return Math.max(3, Math.ceil((projectTicketCount + ticketTons / 20) / 2));
  }, [selectedProjectProfitability, selectedTicket]);

  const recommendedMachineCount = useMemo(() => {
    const ticketMiles = Number(selectedTicket?.miles || 0);
    const projectRiskMultiplier = selectedProjectProfitability?.cost_overrun ? 1 : 0;
    return Math.max(1, Math.ceil(ticketMiles / 25) + projectRiskMultiplier);
  }, [selectedProjectProfitability, selectedTicket]);

  const updateCrewLine = (id: string, patch: Partial<EstimateCrewLine>) => {
    setCrewLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const updateMachineLine = (id: string, patch: Partial<EstimateMachineLine>) => {
    setMachineLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const updateMaterialLine = (id: string, patch: Partial<EstimateMaterialLine>) => {
    setMaterialLines((prev) => prev.map((line) => (line.id === id ? { ...line, ...patch } : line)));
  };

  const applyTicketAndProjectContext = () => {
    if (!selectedTicket) {
      return;
    }

    const materialName = selectedTicket.material || materialLines[0]?.materialName || "Aggregate Base";
    const ticketTons = Number(selectedTicket.tons || 0);
    const ticketYards = Number(selectedTicket.volume_yards || 0);
    const quantity = ticketTons > 0 ? ticketTons : ticketYards > 0 ? ticketYards : materialLines[0]?.quantity || 100;
    const unit = ticketTons > 0 ? "tons" : "cy";
    const preset = materialPresets.find((item) => item.material_name.toLowerCase() === materialName.toLowerCase());
    const densityHint = preset ? Number(preset.density_tons_per_cubic_yard) : null;
    const riskNote = selectedProjectProfitability?.cost_overrun
      ? "Cost overrun risk currently flagged on this project."
      : "No current cost overrun flag on selected project.";

    setMaterialLines((prev) => {
      const first = prev[0] || DEFAULT_MATERIAL_LINES[0];
      return [
        {
          ...first,
          materialName,
          quantity,
          unit,
          unitCost: first.unitCost || 28,
        },
        ...prev.slice(1),
      ];
    });

    setEstimateScope((prev) => {
      const contextBits = [
        selectedProject ? `${selectedProject.project_name} (${selectedProject.project_number})` : "",
        selectedTicket.ticket_number ? `Ticket ${selectedTicket.ticket_number}` : "",
        densityHint ? `Density preset ${densityHint.toFixed(2)} tons/cy` : "",
        riskNote,
      ].filter(Boolean);
      return prev || contextBits.join(". ");
    });

    setEstimateMessage("Applied file and project context to the estimate form.");
  };

  const saveEstimate = async () => {
    if (!estimateName.trim()) {
      setEstimateMessage("Estimate name is required.");
      return;
    }

    const primaryMaterial = materialLines[0] || DEFAULT_MATERIAL_LINES[0];
    const takeoffNumber = `TK-${Date.now().toString().slice(-6)}`;
    const scopeNotes = [
      `Estimate: ${estimateName}`,
      estimateScope,
      `Crew recommendation: ${recommendedCrewHeadcount}`,
      `Machine recommendation: ${recommendedMachineCount}`,
      `Contingency %: ${contingencyPercent}`,
      `Markup %: ${markupPercent}`,
    ]
      .filter(Boolean)
      .join("\n");

    setEstimateSaving(true);
    setEstimateMessage("");
    try {
      const takeoff = await createEstimatorTakeoff({
        project_id: estimateProjectId || null,
        takeoff_number: takeoffNumber,
        material_name: primaryMaterial.materialName,
        quantity: primaryMaterial.quantity.toString(),
        unit_of_measure: primaryMaterial.unit,
        estimated_cost: estimateGrandTotal.toFixed(2),
        status: "draft",
        notes: scopeNotes,
      });

      await createEstimatorVersion({
        project_id: estimateProjectId || null,
        version_name: `${estimateName} v1`,
        revision_number: 1,
        estimated_revenue: estimateGrandTotal.toFixed(2),
        estimated_cost: estimateGrandTotal.toFixed(2),
        status: "draft",
        notes: `Generated from ${takeoff.takeoff_number}`,
      });

      setEstimatorTakeoffs((prev) => [takeoff, ...prev]);
      setEstimateMessage("Estimate saved to Takeoffs and Estimate Versions.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to save estimate.";
      setEstimateMessage(message);
    } finally {
      setEstimateSaving(false);
    }
  };

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);

  const projectManagerText = (key: string) => PROJECT_MANAGER_LABELS[projectManagerLocale][key] || key;

  const toggleProjectManagerLanguage = () => {
    const nextLocale: ProjectManagerLocale = projectManagerLocale === "en" ? "es" : "en";
    setProjectManagerLocale(nextLocale);
    if (typeof window !== "undefined") {
      window.localStorage.setItem("opsflow_locale", nextLocale);
    }
  };

  const handleProjectManagerLogout = () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("opsflow_access_token");
      window.location.href = "/";
    }
  };

  const runProjectManagerAiReview = async (command: string, projectName?: string) => {
    const token = getAccessToken();
    if (!token) {
      setProjectManagerAiMessage("Login required.");
      return;
    }

    setProjectManagerAiRunning(true);
    setProjectManagerAiMessage("");
    const note = [
      `${command}`,
      projectName ? `Project: ${projectName}` : "Project: portfolio",
      `Active projects: ${ownerSummary.activeProjects}`,
      `At-risk projects: ${ownerSummary.topAtRiskProjects.length}`,
      `Open tickets: ${tickets.filter((ticket) => !["resolved", "closed"].includes((ticket.status || "").toLowerCase())).length}`,
      `Pending reports: ${dailyReports.filter((report) => ["draft", "not_started", "pending"].includes((report.status || "").toLowerCase())).length}`,
    ].join("\n");

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/ai/workflow/route`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-ID": getTenantId(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          note,
          company_name: "Project Manager Review",
          reporting_supervisor: "Project Manager",
          project_id: projectManagerActionDraft.projectId || null,
        }),
      });

      if (!response.ok) {
        setProjectManagerAiMessage("AI review could not be completed.");
        return;
      }

      const data = (await response.json()) as { message?: string };
      setProjectManagerAiMessage(data.message || "AI review completed.");
    } catch {
      setProjectManagerAiMessage("AI review could not be completed.");
    } finally {
      setProjectManagerAiRunning(false);
    }
  };

  const createProjectManagerActionTicket = async (actionStatus?: string) => {
    setProjectManagerActionSaving(true);
    setProjectManagerActionMessage("");
    try {
      const created = await createTicket({
        project_id: projectManagerActionDraft.projectId || null,
        ticket_number: `PM-${Date.now().toString().slice(-6)}`,
        material: projectManagerActionDraft.category || "Project Action",
        origin: "Project Manager Module",
        destination: "Operations Queue",
        status: "draft",
        notes: [
          `Action: ${projectManagerActionDraft.title || "Untitled action"}`,
          `Category: ${projectManagerActionDraft.category}`,
          `Priority: ${projectManagerActionDraft.priority}`,
          `Risk: ${projectManagerActionDraft.riskLevel}`,
          `Responsible: ${projectManagerActionDraft.responsiblePerson || "n/a"}`,
          `Due: ${projectManagerActionDraft.dueDate || "n/a"}`,
          `Status: ${actionStatus || projectManagerActionDraft.status}`,
          `Description: ${projectManagerActionDraft.description || "n/a"}`,
          `Notes: ${projectManagerActionDraft.notes || "n/a"}`,
        ].join("\n"),
      });
      setProjectManagerActionMessage(`Action ticket created: ${created.ticket_number || created.id}`);
    } catch {
      setProjectManagerActionMessage("Unable to create action ticket right now.");
    } finally {
      setProjectManagerActionSaving(false);
    }
  };

  const exportProjectManagerPdf = async () => {
    const token = getAccessToken();
    if (!token) {
      setProjectManagerExportMessage("Login required.");
      return;
    }

    const report =
      dailyReports.find((item) => ["submitted", "reviewed", "approved"].includes((item.status || "").toLowerCase())) ||
      dailyReports[0];
    if (!report?.id) {
      setProjectManagerExportMessage("No daily report is available to export yet.");
      return;
    }

    setProjectManagerExportingPdf(true);
    setProjectManagerExportMessage("");
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/daily-field-reports/${report.id}/pdf`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-ID": getTenantId(),
        },
      });
      if (!response.ok) {
        setProjectManagerExportMessage("Unable to export PDF right now.");
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${report.report_number || "daily-report"}.pdf`;
      anchor.click();
      window.URL.revokeObjectURL(url);
      setProjectManagerExportMessage(`Exported PDF for ${report.report_number || report.id}.`);
    } catch {
      setProjectManagerExportMessage("Unable to export PDF right now.");
    } finally {
      setProjectManagerExportingPdf(false);
    }
  };

  const exportProjectManagerExcel = () => {
    if (!projects.length) {
      setProjectManagerExportMessage("No project data is available to export yet.");
      return;
    }

    setProjectManagerExportingExcel(true);
    setProjectManagerExportMessage("");
    try {
      const portfolioRows = projects.map((project) => {
        const projectProfitability = profitability.get(project.id);
        const latestReport = dailyReports.find((report) => report.project_id === project.id);
        const openIssues = tickets.filter(
          (ticket) => ticket.project_id === project.id && !["closed", "resolved"].includes((ticket.status || "").toLowerCase())
        ).length;
        return {
          project_name: project.project_name,
          project_number: project.project_number,
          status: project.status,
          revenue: Number(projectProfitability?.actual_revenue || 0),
          actual_cost: Number(projectProfitability?.actual_cost || 0),
          profit_margin_percent: Number(projectProfitability?.profit_margin || 0),
          open_issues: openIssues,
          latest_daily_report_status: latestReport?.status || "Not Started",
        };
      });

      const alertsRows = [
        ...dailyReports
          .filter((report) => ["draft", "not_started", "pending"].includes((report.status || "").toLowerCase()))
          .map((report) => ({
            project: projects.find((project) => project.id === report.project_id)?.project_name || "Unknown project",
            issue: "Daily report not submitted",
            severity: "High",
            responsible_person: report.reporting_supervisor || "Superintendent",
            report_date: report.report_date || "",
          })),
        ...Array.from(profitability.values())
          .filter((item) => item.cost_overrun || item.revenue_shortfall)
          .map((item) => ({
            project: item.project_name,
            issue: item.cost_overrun ? "Cost code over budget" : "Production below target",
            severity: item.cost_overrun ? "Critical" : "Medium",
            responsible_person: "Project Manager",
            report_date: "",
          })),
      ];

      const dailyReviewRows = dailyReports.map((report) => ({
        report_number: report.report_number || report.id,
        project: projects.find((project) => project.id === report.project_id)?.project_name || "Unknown project",
        report_date: report.report_date || "",
        submitted_by: report.reporting_supervisor || "",
        status: report.status || "",
        work_performed: report.work_performed || "",
      }));

      const performanceRows = projects.map((project) => {
        const item = profitability.get(project.id);
        return {
          project_name: project.project_name,
          project_number: project.project_number,
          status: project.status,
          ticket_count: Number(item?.ticket_count || 0),
          actual_revenue: Number(item?.actual_revenue || 0),
          actual_cost: Number(item?.actual_cost || 0),
          gross_profit: Number(item?.gross_profit || 0),
          profit_margin_percent: Number(item?.profit_margin || 0),
        };
      });

      const actionTicketRows = tickets.map((ticket) => ({
        ticket_number: ticket.ticket_number || ticket.id,
        project: projects.find((project) => project.id === ticket.project_id)?.project_name || "Unassigned",
        material: ticket.material || "",
        driver: ticket.driver || "",
        truck: ticket.truck || "",
        destination: ticket.destination || "",
        status: ticket.status || "",
      }));

      const workbook = XLSX.utils.book_new();
      const appendSheet = (name: string, rows: Record<string, string | number>[]) => {
        const safeRows = rows.length > 0 ? rows : [{ note: "No data available" }];
        const sheet = XLSX.utils.json_to_sheet(safeRows);
        XLSX.utils.book_append_sheet(workbook, sheet, name);
      };

      appendSheet("Portfolio", portfolioRows);
      appendSheet("Alerts", alertsRows);
      appendSheet("Daily Review", dailyReviewRows);
      appendSheet("Performance", performanceRows);
      appendSheet("Action Tickets", actionTicketRows);

      XLSX.writeFile(workbook, `project-manager-export-${new Date().toISOString().slice(0, 10)}.xlsx`, {
        compression: true,
      });
      setProjectManagerExportMessage("Exported project manager workbook (.xlsx).");
    } catch {
      setProjectManagerExportMessage("Unable to export Excel report right now.");
    } finally {
      setProjectManagerExportingExcel(false);
    }
  };

  const renderCompanyOwnerContent = () => {
    if (!detail || !["company_owner", "executive", "project_manager", "estimator", "dispatcher", "accounting", "payroll", "fleet_manager", "safety_manager", "administrator", "customer", "vendor"].includes(detail.roleKey)) {
      return null;
    }

    if (insightsLoading) {
      return (
        <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
          Loading portfolio signals...
        </section>
      );
    }

    if (detail.moduleSlug === "executive-dashboard") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk projects</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Approval backlog</div><div className="mt-2 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Executive signals</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>Assigned tickets in circulation: {ownerSummary.assignedTickets}</p>
              <p>Gross margin tracked: {formatCurrency(ownerSummary.totalMargin)}</p>
              <p>{ownerSummary.approvalPressure ? "Approval pressure is elevated due to stale review tokens." : "Approval queue is within threshold."}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.moduleSlug === "portfolio") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Portfolio projects</h2>
          <div className="mt-4 space-y-3">
            {projects.slice(0, 6).map((project) => {
              const projectProfitability = profitability.get(project.id);
              return (
                <div key={project.id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{project.project_name}</div>
                      <div className="text-sm text-slate-500">{project.project_number} • {project.status}</div>
                    </div>
                    <Link href={`/projects/${project.id}`} className="text-sm font-semibold text-blue-700 hover:underline">Open project</Link>
                  </div>
                  <div className="mt-3 grid gap-3 text-sm text-slate-700 md:grid-cols-3">
                    <div>Revenue: {formatCurrency(Number(projectProfitability?.actual_revenue || 0))}</div>
                    <div>Margin: {Number(projectProfitability?.profit_margin || 0).toFixed(1)}%</div>
                    <div>Tickets: {projectProfitability?.ticket_count || 0}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      );
    }

    if (detail.moduleSlug === "forecasting") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Forecast watchlist</h2>
          <div className="mt-4 space-y-3">
            {ownerSummary.topAtRiskProjects.length === 0 ? (
              <p className="text-sm text-slate-600">No at-risk projects are currently flagged by profitability signals.</p>
            ) : (
              ownerSummary.topAtRiskProjects.map((item) => (
                <div key={item.project_id} className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-slate-800">
                  <div className="font-semibold">{item.project_name}</div>
                  <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}% • Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                  <div className="mt-1">{item.cost_overrun ? "Cost overrun flagged" : ""}{item.cost_overrun && item.revenue_shortfall ? " • " : ""}{item.revenue_shortfall ? "Revenue shortfall flagged" : ""}</div>
                </div>
              ))
            )}
          </div>
        </section>
      );
    }

    if (detail.moduleSlug === "approvals") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Approval backlog</h2>
            <div className="mt-3 text-3xl font-bold text-slate-900">{ownerSummary.flaggedApprovals}</div>
            <p className="mt-2 text-sm text-slate-600">Items exceeding the replay-token alert threshold.</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Unassigned ticket follow-up</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              {ownerSummary.unassignedTickets.length === 0 ? (
                <p>No unassigned tickets currently need owner attention.</p>
              ) : (
                ownerSummary.unassignedTickets.map((ticket) => (
                  <div key={ticket.id} className="rounded-md border border-slate-200 px-3 py-2">
                    {ticket.ticket_number || "Untitled ticket"} • {ticket.material || "Unspecified material"}
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "kpi-board") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Gross margin</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalMargin)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Risk flags</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Executive KPI summary</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              <p>Active projects: {ownerSummary.activeProjects}</p>
              <p>Approval backlog above threshold: {ownerSummary.flaggedApprovals}</p>
              <p>Projects with profitability warnings: {ownerSummary.topAtRiskProjects.length}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "revenue") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Revenue watchlist</h2>
          <div className="mt-4 space-y-3">
            {Array.from(profitability.values()).slice(0, 6).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div className="text-sm text-slate-500">{item.status}</div>
                  </div>
                  <div className="text-right text-sm text-slate-700">
                    <div>Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                    <div>Tickets: {item.ticket_count}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "burn-rate") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Burn rate signals</h2>
          <div className="mt-4 space-y-3">
            {ownerSummary.topAtRiskProjects.length === 0 ? (
              <p className="text-sm text-slate-600">No burn-rate exceptions are currently flagged.</p>
            ) : (
              ownerSummary.topAtRiskProjects.map((item) => (
                <div key={item.project_id} className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-slate-800">
                  <div className="font-semibold">{item.project_name}</div>
                  <div className="mt-1">Gross profit: {formatCurrency(Number(item.gross_profit || 0))}</div>
                  <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                </div>
              ))
            )}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "executive" && detail.moduleSlug === "risk-radar") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Operational risk</h2>
            <div className="mt-3 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div>
            <p className="mt-2 text-sm text-slate-600">Projects currently flagged by profitability warnings.</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Workflow risk</h2>
            <div className="mt-3 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals + ownerSummary.unassignedTickets.length}</div>
            <p className="mt-2 text-sm text-slate-600">Combined stale approval and unassigned ticket follow-up count.</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "projects") {
      const reviewReports = dailyReports.filter((report) => ["submitted", "review", "reviewed", "under_review"].includes((report.status || "").toLowerCase()));
      const dueReports = dailyReports.filter((report) => ["draft", "not_started", "pending"].includes((report.status || "").toLowerCase())).length;
      const awaitingApproval = reviewReports.length;
      const openActionTickets = tickets.filter((ticket) => !["resolved", "closed"].includes((ticket.status || "").toLowerCase())).length;
      const unassignedDispatch = tickets.filter((ticket) => !ticket.driver || !ticket.truck).length;
      const potentialChangeOrders = Math.max(ownerSummary.topAtRiskProjects.length, dailyReports.filter((report) => (report.work_performed || "").toLowerCase().includes("delay")).length);
      const approvalBacklog = ownerSummary.flaggedApprovals + awaitingApproval;

      const projectAlerts = [
        ...dailyReports
          .filter((report) => ["draft", "not_started", "pending"].includes((report.status || "").toLowerCase()))
          .map((report) => ({
            project: projects.find((project) => project.id === report.project_id)?.project_name || "Unknown project",
            issue: "Daily report not submitted",
            severity: "High",
            responsible: report.reporting_supervisor || "Superintendent",
            dateIdentified: report.report_date || new Date().toISOString().slice(0, 10),
            daysOpen: 1,
            action: "Open report and request submission",
          })),
        ...ownerSummary.topAtRiskProjects.map((item) => ({
          project: item.project_name,
          issue: item.cost_overrun ? "Cost code over budget" : "Production below target",
          severity: item.cost_overrun ? "Critical" : "Medium",
          responsible: "Project Manager",
          dateIdentified: new Date().toISOString().slice(0, 10),
          daysOpen: 1,
          action: "Create action ticket and review forecast",
        })),
      ].slice(0, 8);

      const riskProjects = ownerSummary.topAtRiskProjects.length > 0 ? ownerSummary.topAtRiskProjects : projects.slice(0, 3).map((project) => ({
        project_id: project.id,
        project_name: project.project_name,
        status: project.status,
        actual_revenue: 0,
        actual_cost: 0,
        gross_profit: 0,
        profit_margin: 0,
        cost_overrun: false,
        revenue_shortfall: false,
        ticket_count: 0,
      }));

      return (
        <section className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("portfolioSummary")}</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-4 xl:grid-cols-8">
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("activeProjects")}</div><div className="mt-2 text-2xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("projectsAtRisk")}</div><div className="mt-2 text-2xl font-bold text-amber-600">{riskProjects.length}</div></div>
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("dailyReportsDue")}</div><div className="mt-2 text-2xl font-bold text-red-600">{dueReports}</div></div>
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("reportsAwaitingApproval")}</div><div className="mt-2 text-2xl font-bold text-blue-700">{awaitingApproval}</div></div>
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("openActionTickets")}</div><div className="mt-2 text-2xl font-bold text-slate-900">{openActionTickets}</div></div>
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("unassignedDispatchItems")}</div><div className="mt-2 text-2xl font-bold text-amber-600">{unassignedDispatch}</div></div>
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("potentialChangeOrders")}</div><div className="mt-2 text-2xl font-bold text-indigo-700">{potentialChangeOrders}</div></div>
              <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-semibold uppercase text-slate-500">{projectManagerText("approvalBacklog")}</div><div className="mt-2 text-2xl font-bold text-red-700">{approvalBacklog}</div></div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("projectPortfolioView")}</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm text-slate-700">
                <thead className="bg-slate-50 text-xs uppercase text-slate-600">
                  <tr>
                    <th className="px-3 py-2">Project</th>
                    <th className="px-3 py-2">PM / Foreman</th>
                    <th className="px-3 py-2">Status</th>
                    <th className="px-3 py-2">Risk</th>
                    <th className="px-3 py-2">Daily report</th>
                    <th className="px-3 py-2">Open issues</th>
                    <th className="px-3 py-2">Next action</th>
                    <th className="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((project) => {
                    const projectProfitability = profitability.get(project.id);
                    const projectReports = dailyReports.filter((report) => report.project_id === project.id);
                    const latestReport = projectReports[0];
                    const projectRisk = projectProfitability?.cost_overrun || projectProfitability?.revenue_shortfall ? "High" : "Low";
                    const projectOpenIssues = tickets.filter((ticket) => ticket.project_id === project.id && !["closed", "resolved"].includes((ticket.status || "").toLowerCase())).length;

                    return (
                      <tr key={project.id} className="border-t border-slate-200 align-top">
                        <td className="px-3 py-2">
                          <div className="font-semibold text-slate-900">{project.project_name}</div>
                          <div className="text-xs text-slate-500">{project.project_number} • {project.status}</div>
                        </td>
                        <td className="px-3 py-2">Project Manager / {latestReport?.reporting_supervisor || "Foreman"}</td>
                        <td className="px-3 py-2">{project.status}</td>
                        <td className="px-3 py-2">{projectRisk}</td>
                        <td className="px-3 py-2">{latestReport?.status || "Not Started"}</td>
                        <td className="px-3 py-2">{projectOpenIssues}</td>
                        <td className="px-3 py-2">Review production variance</td>
                        <td className="px-3 py-2">
                          <div className="flex flex-wrap gap-2">
                            <Link href={`/projects/${project.id}`} className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100">Open Project</Link>
                            <Link href="/daily-production" className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100">View Daily Reports</Link>
                            <button type="button" onClick={() => runProjectManagerAiReview("Identify Projects at Risk", project.project_name)} className="rounded border border-indigo-300 px-2 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-50">Run AI Review</button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active jobs</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk jobs</div><div className="mt-2 text-3xl font-bold text-amber-600">{riskProjects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Projects at risk</h2>
              <div className="mt-4 space-y-3">
                {riskProjects.map((item) => (
                  <div key={item.project_id} className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-slate-800">
                    <div className="font-semibold">{item.project_name}</div>
                    <div className="mt-1">{item.status} • Margin {Number(item.profit_margin || 0).toFixed(1)}%</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Daily reports awaiting review</h2>
              <div className="mt-4 space-y-3">
                {reviewReports.length === 0 ? (
                  <p className="text-sm text-slate-600">No daily reports are currently waiting for review.</p>
                ) : (
                  reviewReports.slice(0, 4).map((report) => (
                    <div key={report.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                      <div className="font-semibold text-slate-900">{report.report_number || report.id}</div>
                      <div className="mt-1">{report.reporting_supervisor || "Field lead"} • {report.status}</div>
                      <div className="mt-1">{report.work_performed || "Daily production update captured"}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Production performance</h2>
              <div className="mt-4 space-y-3">
                {projects.slice(0, 4).map((project) => {
                  const projectProfitability = profitability.get(project.id);
                  return (
                    <div key={project.id} className="rounded-lg border border-slate-200 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="font-semibold text-slate-900">{project.project_name}</div>
                          <div className="text-sm text-slate-500">{project.project_number} • {project.status}</div>
                        </div>
                        <div className="text-sm text-slate-700">{Number(projectProfitability?.profit_margin || 0).toFixed(1)}% margin</div>
                      </div>
                      <div className="mt-3 grid gap-3 text-sm text-slate-700 md:grid-cols-2">
                        <div>Tickets: {projectProfitability?.ticket_count || 0}</div>
                        <div>Revenue: {formatCurrency(Number(projectProfitability?.actual_revenue || 0))}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Project portfolio</h2>
              <div className="mt-4 space-y-3">
                {projects.slice(0, 4).map((project) => (
                  <div key={project.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{project.project_name}</div>
                        <div>{project.project_number}</div>
                      </div>
                      <Link href={`/projects/${project.id}`} className="font-semibold text-blue-700 hover:underline">Open</Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("projectsNeedingAttention")}</h2>
            <div className="mt-4 space-y-3">
              {projectAlerts.length === 0 ? (
                <p className="text-sm text-slate-600">No alerts currently require project manager action.</p>
              ) : (
                projectAlerts.map((alert, index) => (
                  <div key={`${alert.project}-${alert.issue}-${index}`} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-slate-800">
                    <div className="font-semibold">{alert.project} • {alert.issue}</div>
                    <div className="mt-1">Severity: {alert.severity} • Responsible: {alert.responsible} • Days open: {alert.daysOpen}</div>
                    <div className="mt-1">Recommended action: {alert.action}</div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("laborHours")}</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-2 text-sm text-slate-700">
                <div>Total workers onsite: {employees.length}</div>
                <div>Regular hours: {payrollSummary?.total_regular_hours ?? "0.00"}</div>
                <div>Overtime hours: {payrollSummary?.total_overtime_hours ?? "0.00"}</div>
                <div>Missing timecards: {Math.max(0, ownerSummary.activeProjects - payrollTimecards.length)}</div>
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("machineHours")}</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-2 text-sm text-slate-700">
                <div>Equipment used today: {equipment.length}</div>
                <div>Equipment requiring maintenance: {tickets.filter((ticket) => (ticket.notes || "").toLowerCase().includes("issue")).length}</div>
                <div>Utilization estimate: {equipment.length === 0 ? "0%" : `${Math.min(100, Math.round((ownerSummary.assignedTickets / equipment.length) * 100))}%`}</div>
                <div>Idle estimate: {equipment.length === 0 ? "0%" : `${Math.max(0, 100 - Math.min(100, Math.round((ownerSummary.assignedTickets / equipment.length) * 100)))}%`}</div>
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("materialUsage")}</h2>
              <div className="mt-3 space-y-2 text-sm text-slate-700">
                {tickets.slice(0, 4).map((ticket) => (
                  <div key={ticket.id} className="rounded-md border border-slate-200 px-3 py-2">
                    {ticket.material || "Material"} • {ticket.ticket_number || ticket.id} • {ticket.status}
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("schedulePressure")}</h2>
              <div className="mt-3 space-y-2 text-sm text-slate-700">
                <div>Critical milestones: {riskProjects.length}</div>
                <div>Delayed activities: {dailyReports.filter((report) => (report.work_performed || "").toLowerCase().includes("delay")).length}</div>
                <div>Resource conflicts: {unassignedDispatch}</div>
                <div>Decision constraints: {approvalBacklog}</div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("executionLoad")}</h2>
            <div className="mt-3 grid gap-3 md:grid-cols-3 lg:grid-cols-5">
              <div className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">Assigned action tickets: {openActionTickets}</div>
              <div className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">Unassigned tickets: {unassignedDispatch}</div>
              <div className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">Pending daily reports: {dueReports}</div>
              <div className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">Pending approvals: {approvalBacklog}</div>
              <div className="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-700">Open change-order reviews: {potentialChangeOrders}</div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("actionPlan")}</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <label className="text-sm font-medium text-slate-700">Action title
                <input value={projectManagerActionDraft.title} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, title: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              </label>
              <label className="text-sm font-medium text-slate-700">Project
                <select value={projectManagerActionDraft.projectId} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, projectId: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                  <option value="">Select project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>{project.project_name}</option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700">Category
                <select value={projectManagerActionDraft.category} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, category: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                  <option>Production</option><option>Labor</option><option>Equipment</option><option>Material</option><option>Schedule</option><option>Safety</option><option>Cost</option><option>Change Order</option><option>Other</option>
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700">Priority
                <select value={projectManagerActionDraft.priority} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, priority: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                  <option>Low</option><option>Medium</option><option>High</option><option>Critical</option>
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700">Risk level
                <select value={projectManagerActionDraft.riskLevel} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, riskLevel: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                  <option>Low</option><option>Medium</option><option>High</option><option>Critical</option>
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700">Responsible person
                <input value={projectManagerActionDraft.responsiblePerson} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, responsiblePerson: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              </label>
              <label className="text-sm font-medium text-slate-700">Due date
                <input type="date" value={projectManagerActionDraft.dueDate} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, dueDate: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              </label>
              <label className="text-sm font-medium text-slate-700">Status
                <select value={projectManagerActionDraft.status} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, status: event.target.value }))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm">
                  <option>Open</option><option>Assigned</option><option>In Progress</option><option>Waiting</option><option>Escalated</option><option>Resolved</option><option>Closed</option>
                </select>
              </label>
              <label className="text-sm font-medium text-slate-700 md:col-span-3">Description
                <textarea value={projectManagerActionDraft.description} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, description: event.target.value }))} className="mt-1 min-h-24 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              </label>
              <label className="text-sm font-medium text-slate-700 md:col-span-3">Notes
                <textarea value={projectManagerActionDraft.notes} onChange={(event) => setProjectManagerActionDraft((prev) => ({ ...prev, notes: event.target.value }))} className="mt-1 min-h-20 w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
              </label>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={() => createProjectManagerActionTicket("Open")} disabled={projectManagerActionSaving} className="rounded-lg bg-slate-800 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-900 disabled:opacity-60">{projectManagerText("saveAction")}</button>
              <button type="button" onClick={() => createProjectManagerActionTicket("Assigned")} disabled={projectManagerActionSaving} className="rounded-lg bg-blue-700 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60">{projectManagerText("assignAction")}</button>
              <button type="button" onClick={() => createProjectManagerActionTicket("Escalated")} disabled={projectManagerActionSaving} className="rounded-lg bg-amber-700 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-800 disabled:opacity-60">{projectManagerText("escalate")}</button>
              <button type="button" onClick={() => createProjectManagerActionTicket("Resolved")} disabled={projectManagerActionSaving} className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-60">{projectManagerText("markResolved")}</button>
              <button type="button" onClick={() => createProjectManagerActionTicket("In Progress")} disabled={projectManagerActionSaving} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60">{projectManagerText("createFollowUp")}</button>
              <button type="button" onClick={() => runProjectManagerAiReview("Recommend Next Actions")} disabled={projectManagerAiRunning} className="rounded-lg border border-indigo-300 px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-60">{projectManagerText("runAiAssist")}</button>
            </div>
            {projectManagerActionMessage ? <p className="mt-3 text-sm text-emerald-800">{projectManagerActionMessage}</p> : null}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("marginControl")}</h2>
            {(() => {
              const projectCosts = Array.from(profitability.values()).reduce((sum, item) => sum + Number(item.actual_cost || 0), 0);
              return (
            <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm text-slate-700">
              <div>Original contract value: {formatCurrency(ownerSummary.totalRevenue)}</div>
              <div>Current budget: {formatCurrency(projectCosts)}</div>
              <div>Actual cost to date: {formatCurrency(projectCosts)}</div>
              <div>Forecasted final cost: {formatCurrency(projectCosts * 1.08)}</div>
              <div>Forecasted profit: {formatCurrency(ownerSummary.totalMargin)}</div>
              <div>Forecasted margin: {ownerSummary.totalRevenue > 0 ? `${((ownerSummary.totalMargin / ownerSummary.totalRevenue) * 100).toFixed(1)}%` : "0.0%"}</div>
            </div>
              );
            })()}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">{projectManagerText("aiAssist")}</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {[
                "Summarize Today’s Field Activity",
                "Identify Projects at Risk",
                "Explain Production Variances",
                "Identify Cost Overruns",
                "Find Missing Daily Reports",
                "Review Labor Productivity",
                "Review Equipment Utilization",
                "Review Material Variances",
                "Identify Potential Change Orders",
                "Identify Schedule Threats",
                "Draft Owner Update",
                "Draft Weekly Project Report",
                "Recommend Next Actions",
              ].map((command) => (
                <button key={command} type="button" onClick={() => runProjectManagerAiReview(command)} disabled={projectManagerAiRunning} className="rounded border border-indigo-300 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-60">
                  {command}
                </button>
              ))}
            </div>
            {projectManagerAiMessage ? <p className="mt-3 text-sm text-indigo-800">AI: {projectManagerAiMessage}</p> : null}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "schedule") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Schedule pressure view</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
              <div className="font-semibold text-slate-900">Execution load</div>
              <p className="mt-2">Assigned tickets in play: {ownerSummary.assignedTickets}</p>
              <p>Unassigned tickets needing dispatch: {ownerSummary.unassignedTickets.length}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
              <div className="font-semibold text-slate-900">Projects needing attention</div>
              <p className="mt-2">At-risk projects: {ownerSummary.topAtRiskProjects.length}</p>
              <p>Approval backlog: {ownerSummary.flaggedApprovals}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "rfis") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">RFI follow-up board</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <p>Use intake exceptions and document review to track unresolved project clarifications.</p>
            <p>Approval backlog currently flagged: {ownerSummary.flaggedApprovals}</p>
            <p>Unassigned tickets that may indicate missing field direction: {ownerSummary.unassignedTickets.length}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "submittals") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Submittal readiness</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2 text-sm text-slate-700">
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="font-semibold text-slate-900">Document intake</div>
              <p className="mt-2">Approval backlog above threshold: {ownerSummary.flaggedApprovals}</p>
            </div>
            <div className="rounded-lg border border-slate-200 p-4">
              <div className="font-semibold text-slate-900">Project readiness</div>
              <p className="mt-2">Active jobs ready for document follow-up: {ownerSummary.activeProjects}</p>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "project_manager" && detail.moduleSlug === "change-orders") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Change order watchlist</h2>
          <div className="mt-4 space-y-3">
            {ownerSummary.topAtRiskProjects.length === 0 ? (
              <p className="text-sm text-slate-600">No current change-order risk signals are flagged.</p>
            ) : (
              ownerSummary.topAtRiskProjects.map((item) => (
                <div key={item.project_id} className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-slate-800">
                  <div className="font-semibold">{item.project_name}</div>
                  <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                  <div className="mt-1">Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                </div>
              ))
            )}
          </div>
        </section>
      );
    }

    const driverCounts = tickets.reduce<Map<string, number>>((acc, ticket) => {
      const key = (ticket.driver || "Unassigned driver").trim() || "Unassigned driver";
      acc.set(key, (acc.get(key) || 0) + 1);
      return acc;
    }, new Map());
    const truckCounts = tickets.reduce<Map<string, number>>((acc, ticket) => {
      const key = (ticket.truck || "Unassigned truck").trim() || "Unassigned truck";
      acc.set(key, (acc.get(key) || 0) + 1);
      return acc;
    }, new Map());
    const topDrivers = Array.from(driverCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 4);
    const topTrucks = Array.from(truckCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 4);
    const profitabilityItems = Array.from(profitability.values());
    const totalActualCost = profitabilityItems.reduce((acc, item) => acc + Number(item.actual_cost || 0), 0);
    const totalGrossProfit = profitabilityItems.reduce((acc, item) => acc + Number(item.gross_profit || 0), 0);
    const totalFuelCost = tickets.reduce((acc, ticket) => acc + Number(ticket.fuel_cost || 0), 0);
    const revenueReadyTickets = tickets.filter((ticket) => Number(ticket.revenue || 0) > 0).length;
    const equipmentCount = equipment.length;
    const truckCount = trucks.length;
    const activeTenantUsers = tenantUsers.filter((user) => user.status === "active").length;
    const distinctMaterials = Array.from(new Set(tickets.map((ticket) => ticket.material.trim()).filter(Boolean)));
    const presetCoverage = distinctMaterials.filter((material) => materialPresets.some((preset) => preset.material_name.trim().toLowerCase() === material.toLowerCase())).length;
    const employeeCount = employees.length;

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "dispatch-board") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Unassigned tickets</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.unassignedTickets.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-green-600">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Dispatch backlog</div><div className="mt-2 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Dispatch board</h2>
            <div className="mt-4 space-y-3">
              {tickets.slice(0, 6).map((ticket) => (
                <div key={ticket.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{ticket.ticket_number || "Untitled ticket"}</div>
                      <div>{ticket.material || "Unknown material"} • {ticket.destination || "No destination"}</div>
                    </div>
                    <div className="text-right">
                      <div>Driver: {ticket.driver || "Unassigned"}</div>
                      <div>Truck: {ticket.truck || "Unassigned"}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "crew-calendar") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Driver load</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              {topDrivers.map(([driver, count]) => (
                <div key={driver} className="rounded-md border border-slate-200 px-3 py-2">{driver}: {count} ticket(s)</div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Crew coverage</h2>
            <p className="mt-3 text-sm text-slate-700">Use current driver and truck assignments to balance dispatch load across field crews.</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "route-planning") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Route planning signals</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <p>Unassigned loads needing route planning: {ownerSummary.unassignedTickets.length}</p>
            <p>Assigned loads currently in motion: {ownerSummary.assignedTickets}</p>
            <p>Projects currently receiving loads: {ownerSummary.activeProjects}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "dispatcher" && detail.moduleSlug === "utilization") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Truck utilization</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-700">
              {topTrucks.map(([truck, count]) => (
                <div key={truck} className="rounded-md border border-slate-200 px-3 py-2">{truck}: {count} ticket(s)</div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Capacity view</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned vs unassigned ticket volume provides the current dispatch utilization snapshot.</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "ap") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Actual cost</div><div className="mt-2 text-3xl font-bold text-slate-900">{formatCurrency(totalActualCost)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Fuel cost tracked</div><div className="mt-2 text-3xl font-bold text-red-600">{formatCurrency(totalFuelCost)}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Overrun projects</div><div className="mt-2 text-3xl font-bold text-amber-600">{profitabilityItems.filter((item) => item.cost_overrun).length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked jobs</div><div className="mt-2 text-3xl font-bold text-slate-900">{profitabilityItems.length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "ar") {
      return (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue tracked</div><div className="mt-2 text-3xl font-bold text-green-600">{formatCurrency(ownerSummary.totalRevenue)}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Revenue shortfalls</div><div className="mt-2 text-3xl font-bold text-amber-600">{profitabilityItems.filter((item) => item.revenue_shortfall).length}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Invoice-ready tickets</div><div className="mt-2 text-3xl font-bold text-slate-900">{revenueReadyTickets}</div></div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "invoices") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Invoice-ready ticket flow</h2>
          <div className="mt-4 space-y-3">
            {tickets.slice(0, 6).map((ticket) => (
              <div key={ticket.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{ticket.ticket_number || "Untitled ticket"}</div>
                    <div>{ticket.material || "Unknown material"} • {ticket.driver || "No driver"}</div>
                  </div>
                  <div className="text-right">
                    <div>Revenue: {formatCurrency(Number(ticket.revenue || 0))}</div>
                    <div>Fuel: {formatCurrency(Number(ticket.fuel_cost || 0))}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "accounting" && detail.moduleSlug === "job-cost-ledger") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Job cost ledger</h2>
          <div className="mt-4 space-y-3">
            {profitabilityItems.slice(0, 6).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div>{item.status}</div>
                  </div>
                  <div className="text-right">
                    <div>Cost: {formatCurrency(Number(item.actual_cost || 0))}</div>
                    <div>Profit: {formatCurrency(Number(item.gross_profit || 0))}</div>
                  </div>
                </div>
              </div>
            ))}
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800">
              Total gross profit tracked: {formatCurrency(totalGrossProfit)}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "fleet") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Equipment assets</div><div className="mt-2 text-3xl font-bold text-slate-900">{equipmentCount}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Truck units</div><div className="mt-2 text-3xl font-bold text-blue-700">{truckCount}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Assigned tickets</div><div className="mt-2 text-3xl font-bold text-green-600">{ownerSummary.assignedTickets}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Fuel tracked</div><div className="mt-2 text-3xl font-bold text-red-600">{formatCurrency(totalFuelCost)}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Fleet activity</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2 text-sm text-slate-700">
              <div>
                <div className="font-semibold text-slate-900">Equipment roster</div>
                <div className="mt-2 space-y-2">
                  {equipment.slice(0, 4).map((item) => (
                    <div key={item.id} className="rounded-md border border-slate-200 px-3 py-2">{item.name || item.unit_number || item.id}</div>
                  ))}
                </div>
              </div>
              <div>
                <div className="font-semibold text-slate-900">Truck roster</div>
                <div className="mt-2 space-y-2">
                  {trucks.slice(0, 4).map((item) => (
                    <div key={item.id} className="rounded-md border border-slate-200 px-3 py-2">{item.unit_number || item.name || item.id}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "maintenance") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Maintenance attention</h2>
            <p className="mt-3 text-sm text-slate-700">Equipment assets currently tracked: {equipmentCount}</p>
            <p className="mt-1 text-sm text-slate-700">Truck units currently tracked: {truckCount}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Dispatch impact</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned tickets depending on fleet readiness: {ownerSummary.assignedTickets}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "fuel") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Fuel tracking</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Fuel tracked</div><div className="mt-2 text-2xl font-bold text-red-600">{formatCurrency(totalFuelCost)}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tickets with revenue</div><div className="mt-2 text-2xl font-bold text-slate-900">{revenueReadyTickets}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Truck units</div><div className="mt-2 text-2xl font-bold text-blue-700">{truckCount}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "fleet_manager" && detail.moduleSlug === "work-orders") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Work order queue</h2>
          <div className="mt-4 space-y-2 text-sm text-slate-700">
            <p>Use the equipment and truck rosters as the current work-order source list.</p>
            <p>Fleet-linked dispatch load: {ownerSummary.assignedTickets} assigned tickets.</p>
            <p>Assets currently in the system: {equipmentCount + truckCount}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "incidents") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Incident backlog</div><div className="mt-2 text-3xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">At-risk projects</div><div className="mt-2 text-3xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Unassigned tickets</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.unassignedTickets.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active jobs</div><div className="mt-2 text-3xl font-bold text-slate-900">{ownerSummary.activeProjects}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Incident watchlist</h2>
            <div className="mt-4 space-y-3">
              {ownerSummary.topAtRiskProjects.length === 0 ? (
                <p className="text-sm text-slate-600">No high-risk projects are currently flagged.</p>
              ) : (
                ownerSummary.topAtRiskProjects.map((item) => (
                  <div key={item.project_id} className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-slate-800">
                    <div className="font-semibold">{item.project_name}</div>
                    <div className="mt-1">Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                    <div className="mt-1">Ticket volume: {item.ticket_count}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "inspections") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Inspection pressure</h2>
            <p className="mt-3 text-sm text-slate-700">Stale approval items needing review: {ownerSummary.flaggedApprovals}</p>
            <p className="mt-1 text-sm text-slate-700">Projects with elevated operational risk: {ownerSummary.topAtRiskProjects.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Field coverage</h2>
            <p className="mt-3 text-sm text-slate-700">Assigned tickets currently tied to active work: {ownerSummary.assignedTickets}</p>
            <p className="mt-1 text-sm text-slate-700">Active jobs needing inspection oversight: {ownerSummary.activeProjects}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "toolbox-talks") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Toolbox talk coordination</h2>
          <div className="mt-4 space-y-2 text-sm text-slate-700">
            <p>Active crews inferred from assigned tickets: {ownerSummary.assignedTickets}</p>
            <p>Projects currently active: {ownerSummary.activeProjects}</p>
            <p>Open safety follow-up signals: {ownerSummary.flaggedApprovals + ownerSummary.topAtRiskProjects.length}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "safety_manager" && detail.moduleSlug === "corrective-actions") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Corrective actions queue</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Open actions</div><div className="mt-2 text-2xl font-bold text-red-600">{ownerSummary.flaggedApprovals}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Risk jobs</div><div className="mt-2 text-2xl font-bold text-amber-600">{ownerSummary.topAtRiskProjects.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Unresolved workflow items</div><div className="mt-2 text-2xl font-bold text-slate-900">{ownerSummary.unassignedTickets.length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "user-admin") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tenant users</div><div className="mt-2 text-3xl font-bold text-slate-900">{tenantUsers.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active users</div><div className="mt-2 text-3xl font-bold text-green-600">{activeTenantUsers}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Platform users</div><div className="mt-2 text-3xl font-bold text-blue-700">{adminOverview?.users ?? adminUsers.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Permission catalog</div><div className="mt-2 text-3xl font-bold text-slate-900">{permissionCatalog.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">User access queue</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-700">
              {tenantUsers.slice(0, 5).map((user) => (
                <div key={user.user_id} className="rounded-md border border-slate-200 px-3 py-2">{user.display_name || user.email} • {user.role_name} • {user.status}</div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "role-policies") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Role governance</h2>
            <p className="mt-3 text-sm text-slate-700">Function catalog entries: {permissionCatalog.length}</p>
            <p className="mt-1 text-sm text-slate-700">Tenant members under role control: {tenantUsers.length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Platform scope</h2>
            <p className="mt-3 text-sm text-slate-700">Tenants in overview: {adminOverview?.tenants ?? 0}</p>
            <p className="mt-1 text-sm text-slate-700">Projects in overview: {adminOverview?.projects ?? projects.length}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "audit-logs") {
      return (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Failed integrations</div><div className="mt-2 text-3xl font-bold text-red-600">{serviceInsights?.integration_events_failed ?? 0}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Extraction issues</div><div className="mt-2 text-3xl font-bold text-amber-600">{serviceInsights?.unresolved_extraction_issues ?? 0}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Intake review backlog</div><div className="mt-2 text-3xl font-bold text-slate-900">{serviceInsights?.intake_needs_review ?? 0}</div></div>
        </section>
      );
    }

    if (detail.roleKey === "administrator" && detail.moduleSlug === "integrations") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Integration health</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Pending events</div><div className="mt-2 text-2xl font-bold text-slate-900">{serviceInsights?.integration_events_pending ?? 0}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Failed events</div><div className="mt-2 text-2xl font-bold text-red-600">{serviceInsights?.integration_events_failed ?? 0}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Improvement opportunities</div><div className="mt-2 text-2xl font-bold text-blue-700">{serviceInsights?.opportunities.length ?? 0}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "takeoff") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Takeoffs</div><div className="mt-2 text-3xl font-bold text-slate-900">{estimatorSummary?.takeoff_count ?? estimatorTakeoffs.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Estimate versions</div><div className="mt-2 text-3xl font-bold text-blue-700">{estimatorSummary?.version_count ?? estimatorVersions.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Material presets</div><div className="mt-2 text-3xl font-bold text-green-600">{materialPresets.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Bid pipeline</div><div className="mt-2 text-3xl font-bold text-slate-900">{estimatorSummary?.bid_pipeline_count ?? estimatorBidPipelineItems.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Takeoff inputs</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-700">
              {estimatorTakeoffs.slice(0, 5).map((takeoff) => (
                <div key={takeoff.id} className="rounded-md border border-slate-200 px-3 py-2">{takeoff.takeoff_number} • {takeoff.material_name || "Unknown material"} • {takeoff.quantity} {takeoff.unit_of_measure}</div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-blue-900">Editable estimate worksheet</h2>
            <p className="mt-2 text-sm text-blue-900">
              Build a working estimate using project context, extracted ticket data, crew mix, equipment, and materials.
            </p>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="text-sm font-medium text-slate-700">
                Estimate name
                <input
                  value={estimateName}
                  onChange={(event) => setEstimateName(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </label>

              <label className="text-sm font-medium text-slate-700">
                Project context
                <select
                  value={estimateProjectId}
                  onChange={(event) => setEstimateProjectId(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">Select project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>{project.project_name} ({project.project_number})</option>
                  ))}
                </select>
              </label>

              <label className="text-sm font-medium text-slate-700">
                File/ticket context
                <select
                  value={estimateTicketId}
                  onChange={(event) => setEstimateTicketId(event.target.value)}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">Select ticket/extracted file</option>
                  {tickets.map((ticket) => (
                    <option key={ticket.id} value={ticket.id}>{ticket.ticket_number || ticket.id} • {ticket.material || "Material n/a"}</option>
                  ))}
                </select>
              </label>

              <label className="text-sm font-medium text-slate-700">
                Scope description
                <input
                  value={estimateScope}
                  onChange={(event) => setEstimateScope(event.target.value)}
                  placeholder="Describe scope and estimating assumptions"
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </label>

              <label className="text-sm font-medium text-slate-700">
                Contingency (%)
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={contingencyPercent}
                  onChange={(event) => setContingencyPercent(Number(event.target.value || 0))}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </label>

              <label className="text-sm font-medium text-slate-700">
                Markup (%)
                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={markupPercent}
                  onChange={(event) => setMarkupPercent(Number(event.target.value || 0))}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                />
              </label>
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={applyTicketAndProjectContext}
                className="inline-flex rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
              >
                Apply File + Project Context
              </button>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Crew</h3>
                <div className="mt-2 space-y-2">
                  {crewLines.map((line) => (
                    <div key={line.id} className="grid grid-cols-4 gap-1 text-xs">
                      <input value={line.crewType} onChange={(event) => updateCrewLine(line.id, { crewType: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.headcount} onChange={(event) => updateCrewLine(line.id, { headcount: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.hourlyRate} onChange={(event) => updateCrewLine(line.id, { hourlyRate: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.hours} onChange={(event) => updateCrewLine(line.id, { hours: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-xs text-slate-600">Recommended crew headcount: {recommendedCrewHeadcount}</p>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Machines</h3>
                <div className="mt-2 space-y-2">
                  {machineLines.map((line) => (
                    <div key={line.id} className="grid grid-cols-4 gap-1 text-xs">
                      <input value={line.machineType} onChange={(event) => updateMachineLine(line.id, { machineType: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.count} onChange={(event) => updateMachineLine(line.id, { count: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.hourlyRate} onChange={(event) => updateMachineLine(line.id, { hourlyRate: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.hours} onChange={(event) => updateMachineLine(line.id, { hours: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                    </div>
                  ))}
                </div>
                <p className="mt-2 text-xs text-slate-600">Recommended machine count: {recommendedMachineCount}</p>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">Materials</h3>
                <div className="mt-2 space-y-2">
                  {materialLines.map((line) => (
                    <div key={line.id} className="grid grid-cols-4 gap-1 text-xs">
                      <input value={line.materialName} onChange={(event) => updateMaterialLine(line.id, { materialName: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.quantity} onChange={(event) => updateMaterialLine(line.id, { quantity: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                      <input value={line.unit} onChange={(event) => updateMaterialLine(line.id, { unit: event.target.value })} className="rounded border border-slate-300 px-2 py-1" />
                      <input type="number" value={line.unitCost} onChange={(event) => updateMaterialLine(line.id, { unitCost: Number(event.target.value || 0) })} className="rounded border border-slate-300 px-2 py-1" />
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">Crew: {formatCurrency(crewCost)}</div>
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">Machines: {formatCurrency(machineCost)}</div>
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">Materials: {formatCurrency(materialCost)}</div>
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">Contingency: {formatCurrency(estimateContingency)}</div>
              <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">Markup: {formatCurrency(estimateMarkup)}</div>
              <div className="rounded-lg border border-blue-300 bg-blue-100 p-3 text-sm font-semibold text-blue-900">Total estimate: {formatCurrency(estimateGrandTotal)}</div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={saveEstimate}
                disabled={estimateSaving}
                className="inline-flex rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-60"
              >
                {estimateSaving ? "Saving..." : "Save Estimate"}
              </button>
              {estimateMessage ? <span className="text-sm text-slate-700">{estimateMessage}</span> : null}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "estimate-versions") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Estimate version signals</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Versions</div><div className="mt-2 text-2xl font-bold text-slate-900">{estimatorSummary?.version_count ?? estimatorVersions.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Submitted versions</div><div className="mt-2 text-2xl font-bold text-blue-700">{estimatorVersions.filter((item) => item.status === "submitted").length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Draft versions</div><div className="mt-2 text-2xl font-bold text-amber-600">{estimatorVersions.filter((item) => item.status === "draft").length}</div></div>
          </div>
          <div className="mt-4 space-y-3">
            {estimatorVersions.slice(0, 5).map((version) => (
              <div key={version.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="font-semibold text-slate-900">{version.version_name} r{version.revision_number}</div>
                <div className="mt-1">Revenue: {formatCurrency(Number(version.estimated_revenue || 0))} • Cost: {formatCurrency(Number(version.estimated_cost || 0))}</div>
                <div className="mt-1">Status: {version.status}</div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "bid-pipeline") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Bid pipeline</h2>
          <div className="mt-4 space-y-3">
            {estimatorBidPipelineItems.slice(0, 6).map((bid) => {
              return (
                <div key={bid.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="font-semibold text-slate-900">{bid.bid_number}</div>
                      <div>{bid.customer_name || "Unknown customer"} • {bid.stage}</div>
                    </div>
                    <div className="text-right">
                      <div>Bid amount: {formatCurrency(Number(bid.bid_amount || 0))}</div>
                      <div>Probability: {Number(bid.probability_percent || 0).toFixed(1)}%</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "estimator" && detail.moduleSlug === "win-loss") {
      return (
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Wins</div><div className="mt-2 text-3xl font-bold text-green-600">{estimatorSummary?.wins ?? estimatorWinLossRecords.filter((item) => item.outcome === "won").length}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Losses</div><div className="mt-2 text-3xl font-bold text-red-600">{estimatorSummary?.losses ?? estimatorWinLossRecords.filter((item) => item.outcome === "lost").length}</div></div>
          <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Win rate</div><div className="mt-2 text-3xl font-bold text-slate-900">{Number(estimatorSummary?.win_rate_percent || 0).toFixed(1)}%</div></div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "project-snapshot") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked projects</div><div className="mt-2 text-3xl font-bold text-slate-900">{customerPortalProjects.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-blue-700">{customerPortalProjects.filter((project) => project.status === "active").length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Project revenue</div><div className="mt-2 text-3xl font-bold text-green-600">{formatCurrency(customerPortalProjects.reduce((sum, project) => sum + Number(project.actual_revenue || 0), 0))}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Project tickets</div><div className="mt-2 text-3xl font-bold text-slate-900">{customerPortalProjects.reduce((sum, project) => sum + project.ticket_count, 0)}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Customer project snapshot</h2>
            <div className="mt-4 space-y-3">
              {customerPortalProjects.slice(0, 5).map((project) => {
                return (
                  <div key={project.project_id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="font-semibold text-slate-900">{project.project_name}</div>
                        <div>{project.project_number} • {project.status}</div>
                      </div>
                      <div className="text-right">
                        <div>Revenue: {formatCurrency(Number(project.actual_revenue || 0))}</div>
                        <div>Tickets: {project.ticket_count}</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "milestones") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Milestone progress</h2>
            <p className="mt-3 text-sm text-slate-700">Active projects currently visible: {customerPortalProjects.filter((project) => project.status === "active").length}</p>
            <p className="mt-1 text-sm text-slate-700">Projects with pending document review: {customerPortalProjects.filter((project) => project.pending_review_documents > 0).length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Delivery readiness</h2>
            <p className="mt-3 text-sm text-slate-700">Tracked project tickets in circulation: {customerPortalProjects.reduce((sum, project) => sum + project.ticket_count, 0)}</p>
            <p className="mt-1 text-sm text-slate-700">Pending document review items: {customerPortalProjects.reduce((sum, project) => sum + project.pending_review_documents, 0)}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "documents") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Document visibility</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Review backlog</div><div className="mt-2 text-2xl font-bold text-amber-600">{customerPortalDocuments.reduce((sum, item) => sum + item.pending_review_documents, 0)}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Tracked projects</div><div className="mt-2 text-2xl font-bold text-slate-900">{customerPortalProjects.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Documents</div><div className="mt-2 text-2xl font-bold text-blue-700">{customerPortalDocuments.reduce((sum, item) => sum + item.total_documents, 0)}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "customer" && detail.moduleSlug === "billing-status") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Billing status</h2>
          <div className="mt-4 space-y-3">
            {customerPortalBilling.slice(0, 5).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div>{item.status}</div>
                  </div>
                  <div className="text-right">
                    <div>Revenue: {formatCurrency(Number(item.actual_revenue || 0))}</div>
                    <div>Tickets: {item.ticket_count}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "purchase-orders") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Purchase orders</div><div className="mt-2 text-3xl font-bold text-slate-900">{vendorPurchaseOrders.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Delivery records</div><div className="mt-2 text-3xl font-bold text-blue-700">{vendorDeliveryRecords.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Open review items</div><div className="mt-2 text-3xl font-bold text-amber-600">{vendorComplianceDocuments.filter((item) => item.status !== "current").length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Submitted invoices</div><div className="mt-2 text-3xl font-bold text-green-600">{vendorInvoiceSubmissions.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Purchase order context</h2>
            <div className="mt-4 space-y-3">
              {vendorPurchaseOrders.slice(0, 5).map((purchaseOrder) => (
                <div key={purchaseOrder.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                  <div className="font-semibold text-slate-900">{purchaseOrder.po_number}</div>
                  <div>{purchaseOrder.vendor_name || "Unknown vendor"} • {purchaseOrder.status}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "invoice-submit") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Invoice submit queue</h2>
          <div className="mt-4 space-y-3">
            {vendorInvoiceSubmissions.slice(0, 5).map((invoice) => (
              <div key={invoice.id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{invoice.invoice_number}</div>
                    <div>{invoice.vendor_name || "Unknown vendor"} • {invoice.status}</div>
                  </div>
                  <div className="text-right">
                    <div>Amount: {formatCurrency(Number(invoice.amount || 0))}</div>
                    <div>Status: {invoice.status}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "delivery-tracking") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Delivery tracking</h2>
            <p className="mt-3 text-sm text-slate-700">Delivery records tracked: {vendorDeliveryRecords.length}</p>
            <p className="mt-1 text-sm text-slate-700">Delivered records: {vendorDeliveryRecords.filter((item) => item.status === "delivered").length}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Project drop-offs</h2>
            <p className="mt-3 text-sm text-slate-700">Projects receiving vendor deliveries: {new Set(vendorDeliveryRecords.map((item) => item.project_id).filter(Boolean)).size}</p>
            <p className="mt-1 text-sm text-slate-700">Pending delivery records: {vendorDeliveryRecords.filter((item) => item.status !== "delivered").length}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "vendor" && detail.moduleSlug === "compliance-docs") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Compliance document status</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Compliance docs</div><div className="mt-2 text-2xl font-bold text-slate-900">{vendorComplianceDocuments.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Current docs</div><div className="mt-2 text-2xl font-bold text-green-600">{vendorComplianceDocuments.filter((item) => item.status === "current").length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Needs follow-up</div><div className="mt-2 text-2xl font-bold text-amber-600">{vendorComplianceDocuments.filter((item) => item.status !== "current").length}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "timecards") {
      return (
        <section className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Employees</div><div className="mt-2 text-3xl font-bold text-slate-900">{payrollSummary?.employee_count ?? employeeCount}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Active projects</div><div className="mt-2 text-3xl font-bold text-blue-700">{ownerSummary.activeProjects}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Timecards</div><div className="mt-2 text-3xl font-bold text-green-600">{payrollSummary?.timecard_count ?? payrollTimecards.length}</div></div>
            <div className="rounded-xl border border-slate-200 bg-white p-4"><div className="text-xs font-semibold uppercase text-slate-500">Payroll runs</div><div className="mt-2 text-3xl font-bold text-slate-900">{payrollSummary?.payroll_run_count ?? payrollRuns.length}</div></div>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Timecard roster</h2>
            <div className="mt-4 space-y-2 text-sm text-slate-700">
              {payrollTimecards.slice(0, 5).map((timecard) => (
                <div key={timecard.id} className="rounded-md border border-slate-200 px-3 py-2">
                  {timecard.work_description || timecard.employee_id} • {timecard.regular_hours}h regular / {timecard.overtime_hours}h OT
                </div>
              ))}
            </div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "overtime") {
      return (
        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Overtime pressure</h2>
            <p className="mt-3 text-sm text-slate-700">Overtime hours tracked: {payrollSummary?.total_overtime_hours ?? "0.00"}</p>
            <p className="mt-1 text-sm text-slate-700">Double-time hours tracked: {payrollSummary?.total_double_time_hours ?? "0.00"}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Workload context</h2>
            <p className="mt-3 text-sm text-slate-700">Employees currently tracked: {employeeCount}</p>
            <p className="mt-1 text-sm text-slate-700">Active jobs in the tenant: {ownerSummary.activeProjects}</p>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "payroll-runs") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Payroll run readiness</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Employee roster</div><div className="mt-2 text-2xl font-bold text-slate-900">{payrollSummary?.employee_count ?? employeeCount}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Payroll runs</div><div className="mt-2 text-2xl font-bold text-blue-700">{payrollRuns.length}</div></div>
            <div className="rounded-lg border border-slate-200 p-4"><div className="text-xs font-semibold uppercase text-slate-500">Regular hours</div><div className="mt-2 text-2xl font-bold text-green-600">{payrollSummary?.total_regular_hours ?? "0.00"}</div></div>
          </div>
        </section>
      );
    }

    if (detail.roleKey === "payroll" && detail.moduleSlug === "labor-cost-allocation") {
      return (
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Labor cost allocation</h2>
          <div className="mt-4 space-y-3">
            {Array.from(profitability.values()).slice(0, 5).map((item) => (
              <div key={item.project_id} className="rounded-lg border border-slate-200 p-4 text-sm text-slate-700">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-900">{item.project_name}</div>
                    <div>{item.status}</div>
                  </div>
                  <div className="text-right">
                    <div>Cost: {formatCurrency(Number(item.actual_cost || 0))}</div>
                    <div>Margin: {Number(item.profit_margin || 0).toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      );
    }

    return null;
  };

  if (!roleAccessResolved) {
    return (
      <AppShell titleKey="modules.title">
        <div className="space-y-4 p-6">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">Loading module access...</div>
        </div>
      </AppShell>
    );
  }

  if (!detail) {
    return (
      <AppShell titleKey="modules.title">
        <div className="space-y-4 p-6">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <h2 className="text-lg font-semibold text-red-900">Module route not found</h2>
            <p className="mt-1 text-sm text-red-800">The requested role/module combination does not exist in the current module catalog.</p>
          </div>
          <Link href="/modules" className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline">
            Back to Modules
          </Link>
        </div>
      </AppShell>
    );
  }

  if (!canAccessModuleRole(roleAccess, detail.roleKey)) {
    return (
      <AppShell titleKey="modules.title">
        <div className="space-y-4 p-6">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <h2 className="text-lg font-semibold text-red-900">Module access denied</h2>
            <p className="mt-1 text-sm text-red-800">This module role workspace is not available for your current account role.</p>
          </div>
          <Link href="/modules" className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline">
            Back to Modules
          </Link>
        </div>
      </AppShell>
    );
  }

  const isProjectManagerProjects = detail.roleKey === "project_manager" && detail.moduleSlug === "projects";

  return (
    <AppShell titleKey="modules.title">
      <div className="space-y-6 p-6">
        {!isProjectManagerProjects ? (
          <div className="mb-2">
            <Link href="/modules" className="inline-flex text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline">
              Back to Modules
            </Link>
          </div>
        ) : null}

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{isProjectManagerProjects ? projectManagerText("projectManager") : detail.roleLabel}</span>
            {!isProjectManagerProjects ? (
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                  detail.route.status === "live" ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"
                }`}
              >
                {detail.route.status === "live" ? "Live Module" : "Bridge Module"}
              </span>
            ) : (
              <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-800">Operational Dashboard</span>
            )}
          </div>

          <h1 className="text-3xl font-bold text-slate-900">{isProjectManagerProjects ? projectManagerText("projectManager") : detail.moduleLabel}</h1>
          <p className="mt-2 text-sm text-slate-600">{detail.roleSummary}</p>
          <p className="mt-2 text-sm text-slate-700">{isProjectManagerProjects ? "Plan, execute, monitor, and control active construction projects with daily production signals and approvals." : detail.route.helperText}</p>

          {isProjectManagerProjects ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Link href="/workspace" className="rounded-lg bg-blue-700 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-800">{projectManagerText("createProject")}</Link>
              <Link href="/daily-production" className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100">{projectManagerText("openDailyProduction")}</Link>
              <Link href="/daily-production/queue" className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100">{projectManagerText("reviewApprovals")}</Link>
              <button type="button" onClick={() => createProjectManagerActionTicket("Open")} disabled={projectManagerActionSaving} className="rounded-lg border border-emerald-300 px-3 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 disabled:opacity-60">{projectManagerText("createActionTicket")}</button>
              <button type="button" onClick={() => runProjectManagerAiReview("Summarize Today’s Field Activity")} disabled={projectManagerAiRunning} className="rounded-lg border border-indigo-300 px-3 py-2 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-60">{projectManagerText("runAiReview")}</button>
              <button type="button" onClick={exportProjectManagerPdf} disabled={projectManagerExportingPdf} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60">{projectManagerExportingPdf ? "Exporting..." : projectManagerText("exportPdf")}</button>
              <button type="button" onClick={exportProjectManagerExcel} disabled={projectManagerExportingExcel} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-60">{projectManagerExportingExcel ? "Exporting..." : projectManagerText("exportExcel")}</button>
              <button type="button" onClick={toggleProjectManagerLanguage} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100">{projectManagerText("switchLanguage")}</button>
              <Link href="/modules" className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100">{projectManagerText("backToModules")}</Link>
              <button type="button" onClick={handleProjectManagerLogout} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100">{projectManagerText("logout")}</button>
            </div>
          ) : null}
          {isProjectManagerProjects && projectManagerExportMessage ? <p className="mt-2 text-sm text-slate-700">{projectManagerExportMessage}</p> : null}

          {detail.route.status === "bridge" && !isProjectManagerProjects ? (
            <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-amber-900">Bridge workspace form</h2>
              <p className="mt-2 text-sm text-amber-900">
                Capture ownership, risk, margin, and next actions here while this module is bridged to core workflows.
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <label className="text-sm font-medium text-slate-700">
                  Initiative
                  <input
                    value={bridgeDraft.initiative}
                    onChange={(event) => setBridgeDraft((prev) => ({ ...prev, initiative: event.target.value }))}
                    placeholder={`${detail.moduleLabel} action plan`}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Portfolio view / scope
                  <input
                    value={bridgeDraft.portfolioView}
                    onChange={(event) => setBridgeDraft((prev) => ({ ...prev, portfolioView: event.target.value }))}
                    placeholder="Example: Q3 heavy civil portfolio"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Risk level
                  <select
                    value={bridgeDraft.riskLevel}
                    onChange={(event) =>
                      setBridgeDraft((prev) => ({
                        ...prev,
                        riskLevel: event.target.value as BridgeWorkspaceDraft["riskLevel"],
                      }))
                    }
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Margin target (%)
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={bridgeDraft.marginTarget}
                    onChange={(event) => setBridgeDraft((prev) => ({ ...prev, marginTarget: event.target.value }))}
                    placeholder="12.5"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Action owner
                  <input
                    value={bridgeDraft.owner}
                    onChange={(event) => setBridgeDraft((prev) => ({ ...prev, owner: event.target.value }))}
                    placeholder="Name or email"
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700">
                  Due date
                  <input
                    type="date"
                    value={bridgeDraft.dueDate}
                    onChange={(event) => setBridgeDraft((prev) => ({ ...prev, dueDate: event.target.value }))}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </label>
                <label className="text-sm font-medium text-slate-700 md:col-span-2">
                  Linked project
                  <select
                    value={bridgeDraft.linkedProjectId}
                    onChange={(event) => setBridgeDraft((prev) => ({ ...prev, linkedProjectId: event.target.value }))}
                    className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  >
                    <option value="">Select project context</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.project_name} ({project.project_number})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium text-slate-700 md:col-span-2">
                  Notes / decisions
                  <textarea
                    value={bridgeDraft.notes}
                    onChange={(event) => setBridgeDraft((prev) => ({ ...prev, notes: event.target.value }))}
                    placeholder="Track portfolio visibility decisions, risk actions, approvals, and follow-ups."
                    className="mt-1 min-h-28 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
                  />
                </label>
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={saveBridgeDraft}
                  className="inline-flex items-center rounded-lg bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-800"
                >
                  Save Bridge Workspace
                </button>
                <button
                  type="button"
                  onClick={resetBridgeDraft}
                  className="inline-flex items-center rounded-lg border border-amber-300 px-4 py-2 text-sm font-semibold text-amber-900 hover:bg-amber-100"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={runBridgeAiAssist}
                  className="inline-flex items-center rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800"
                >
                  Run AI Assist
                </button>
                <button
                  type="button"
                  onClick={createBridgeActionTicket}
                  disabled={bridgeActionSaving}
                  className="inline-flex items-center rounded-lg bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-60"
                >
                  {bridgeActionSaving ? "Creating..." : "Create Action Ticket"}
                </button>
                {bridgeDraftMessage ? <span className="text-sm text-amber-900">{bridgeDraftMessage}</span> : null}
              </div>
              {bridgeAiMessage ? <p className="mt-3 text-sm text-indigo-800">AI: {bridgeAiMessage}</p> : null}
              {bridgeActionMessage ? <p className="mt-2 text-sm text-emerald-800">{bridgeActionMessage}</p> : null}
            </div>
          ) : null}

          {detail.route.focusAreas?.length && !isProjectManagerProjects ? (
            <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Focus areas</h2>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {detail.route.focusAreas.map((item) => (
                  <div key={item} className="rounded-md bg-white px-3 py-2 text-sm text-slate-700 shadow-sm">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {detail.route.actionLinks?.length && !isProjectManagerProjects ? (
            <div className="mt-6 rounded-lg border border-slate-200 bg-white p-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">Recommended actions</h2>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {detail.route.actionLinks.map((action) => (
                  <Link
                    key={`${detail.moduleSlug}-${action.label}`}
                    href={action.href}
                    className="rounded-lg border border-slate-200 px-4 py-3 text-sm font-semibold text-slate-800 transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800"
                  >
                    {action.label}
                  </Link>
                ))}
              </div>
            </div>
          ) : null}

          {!isProjectManagerProjects ? (
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Link
                href={detail.route.href}
                className="inline-flex items-center rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800"
              >
                {detail.route.primaryActionLabel || "Open Module Workspace"}
              </Link>
              <Link
                href="/modules"
                className="inline-flex items-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100"
              >
                Browse Other Modules
              </Link>
            </div>
          ) : null}
        </section>

        {renderCompanyOwnerContent()}
      </div>
    </AppShell>
  );
}
