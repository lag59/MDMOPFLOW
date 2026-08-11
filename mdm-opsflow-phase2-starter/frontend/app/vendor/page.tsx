"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getAccessToken, getTenantId } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/i18n";
import type {
  VendorPurchaseOrder, VendorInvoiceSubmission,
  VendorDeliveryRecord, VendorComplianceDocument,
} from "@/lib/vendor";

// ── helpers ──────────────────────────────────────────────────────────────────

const fmt = (n: string | number | null | undefined) =>
  !n || n === "0" ? "—" : Number(n).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

type StatusColor = { bg: string; text: string };
const statusStyle = (status: string): StatusColor => {
  const s = (status || "").toLowerCase();
  if (["approved","received","active","paid","current"].some(k => s.includes(k))) return { bg: "#dcfce7", text: "#166534" };
  if (["pending","submitted","in_transit","review"].some(k => s.includes(k)))     return { bg: "#eff6ff", text: "#1d4ed8" };
  if (["rejected","expired","cancelled","overdue"].some(k => s.includes(k)))      return { bg: "#fee2e2", text: "#991b1b" };
  return { bg: "#f1f5f9", text: "#475569" };
};

const Pill = ({ status }: { status: string }) => {
  const { bg, text } = statusStyle(status);
  return (
    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 9px", borderRadius: 999,
      background: bg, color: text, textTransform: "capitalize", whiteSpace: "nowrap" }}>
      {status.replace(/_/g, " ")}
    </span>
  );
};

type Tab = "pos" | "invoices" | "deliveries" | "compliance";
type Project = { id: string; project_name: string; project_number: string };
type Msg = { text: string; ok: boolean };

// ── component ────────────────────────────────────────────────────────────────

export default function VendorPortalPage() {
  const [tab, setTab]               = useState<Tab>("pos");
  const [projects, setProjects]     = useState<Project[]>([]);
  const [pos, setPos]               = useState<VendorPurchaseOrder[]>([]);
  const [invoices, setInvoices]     = useState<VendorInvoiceSubmission[]>([]);
  const [deliveries, setDeliveries] = useState<VendorDeliveryRecord[]>([]);
  const [compliance, setCompliance] = useState<VendorComplianceDocument[]>([]);
  const [loading, setLoading]       = useState(true);
  const [msg, setMsg]               = useState<Msg | null>(null);
  const [saving, setSaving]         = useState(false);
  const [showForm, setShowForm]     = useState(false);

  // PO form
  const [poForm, setPoForm] = useState({ po_number: "", vendor_name: "", description: "", project_id: "", status: "pending", total_amount: "" });
  // Invoice form
  const [invForm, setInvForm] = useState({ invoice_number: "", vendor_name: "", amount: "", purchase_order_id: "", project_id: "", status: "submitted", notes: "" });
  // Delivery form
  const [delForm, setDelForm] = useState({ ticket_number: "", vendor_name: "", destination: "", purchase_order_id: "", project_id: "", status: "in_transit", received_at: "" });
  // Compliance form
  const [compForm, setCompForm] = useState({ document_name: "", vendor_name: "", project_id: "", status: "active", expires_at: "", notes: "" });

  const api    = getApiBaseUrl();
  const token  = getAccessToken();
  const tenant = getTenantId();

  function h() {
    return { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "X-Tenant-ID": tenant };
  }

  async function load() {
    const [projRes, poRes, invRes, delRes, compRes] = await Promise.all([
      fetch(`${api}/api/projects`, { headers: h() }),
      fetch(`${api}/api/vendor/purchase-orders`, { headers: h() }),
      fetch(`${api}/api/vendor/invoice-submissions`, { headers: h() }),
      fetch(`${api}/api/vendor/delivery-records`, { headers: h() }),
      fetch(`${api}/api/vendor/compliance-documents`, { headers: h() }),
    ]);
    if (projRes.ok) setProjects(await projRes.json());
    if (poRes.ok)   setPos(await poRes.json());
    if (invRes.ok)  setInvoices(await invRes.json());
    if (delRes.ok)  setDeliveries(await delRes.json());
    if (compRes.ok) setCompliance(await compRes.json());
    setLoading(false);
  }

  useEffect(() => {
    if (!token) { window.location.href = "/login"; return; }
    load();
  }, []);

  // ── generic POST helper
  async function create(path: string, body: object, onSuccess: (data: unknown) => void) {
    setSaving(true); setMsg(null);
    const r = await fetch(`${api}${path}`, { method: "POST", headers: h(), body: JSON.stringify(body) });
    setSaving(false);
    if (r.ok) {
      onSuccess(await r.json());
      setShowForm(false);
      setMsg({ text: "Created successfully.", ok: true });
    } else {
      const d = await r.json().catch(() => null);
      setMsg({ text: d?.detail || "Failed to create.", ok: false });
    }
  }

  // ── metrics
  const counts = {
    pos:        pos.length,
    pendingPos: pos.filter(p => p.status === "pending").length,
    invoices:   invoices.length,
    pendingInv: invoices.filter(i => i.status === "submitted").length,
    deliveries: deliveries.length,
    inTransit:  deliveries.filter(d => d.status === "in_transit").length,
    compliance: compliance.length,
    expiring:   compliance.filter(c => {
      if (!c.expires_at) return false;
      const d = new Date(c.expires_at);
      return d <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
    }).length,
  };

  const TAB_LABELS: Record<Tab, string> = {
    pos: `Purchase Orders (${counts.pos})`,
    invoices: `Invoices (${counts.invoices})`,
    deliveries: `Deliveries (${counts.deliveries})`,
    compliance: `Compliance (${counts.compliance})`,
  };

  const projOpts = projects.map(p => ({ value: p.id, label: `${p.project_name} (${p.project_number})` }));
  const poOpts   = pos.map(p => ({ value: p.id, label: `${p.po_number} – ${p.vendor_name}` }));

  return (
    <AppShell titleKey="nav.vendor">
      {loading ? <p className="muted">Loading…</p> : (
        <>
          {/* Metrics */}
          <div className="grid" style={{ gridTemplateColumns: "repeat(4,1fr)", marginBottom: 20 }}>
            {[
              { label: "Purchase Orders",  value: counts.pos,        sub: `${counts.pendingPos} pending`,   color: "#2563eb" },
              { label: "Invoice Subs.",    value: counts.invoices,   sub: `${counts.pendingInv} submitted`, color: "#d97706" },
              { label: "Deliveries",       value: counts.deliveries, sub: `${counts.inTransit} in transit`, color: "#16a34a" },
              { label: "Compliance Docs",  value: counts.compliance, sub: `${counts.expiring} expiring soon`, color: counts.expiring > 0 ? "#dc2626" : "#7c3aed" },
            ].map(m => (
              <div className="card" key={m.label}>
                <div className="metric-note">{m.label}</div>
                <div className="metric" style={{ color: m.color }}>{m.value}</div>
                <div className="metric-note">{m.sub}</div>
              </div>
            ))}
          </div>

          {msg && (
            <div style={{ marginBottom: 14, padding: "9px 14px", borderRadius: 8, fontSize: 13,
              background: msg.ok ? "#dcfce7" : "#fee2e2", color: msg.ok ? "#166534" : "#991b1b" }}>
              {msg.text}
            </div>
          )}

          {/* Tab bar + add button */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", marginBottom: 16 }}>
            <div style={{ display: "flex", gap: 2 }}>
              {(Object.keys(TAB_LABELS) as Tab[]).map(t => (
                <button key={t} onClick={() => { setTab(t); setShowForm(false); setMsg(null); }}
                  className={tab === t ? "" : "btn-ghost"}
                  style={{ fontSize: 12, padding: "7px 14px", borderRadius: "8px 8px 0 0",
                    borderBottom: tab === t ? "2px solid #f97316" : "2px solid transparent" }}>
                  {TAB_LABELS[t]}
                </button>
              ))}
            </div>
            <button onClick={() => { setShowForm(v => !v); setMsg(null); }} style={{ fontSize: 12, padding: "6px 14px", marginBottom: 4 }}>
              {showForm ? "✕ Cancel" : "+ New"}
            </button>
          </div>

          {/* ── Purchase Orders ── */}
          {tab === "pos" && (
            <>
              {showForm && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <h3 style={{ marginTop: 0, fontSize: 14 }}>New Purchase Order</h3>
                  <form onSubmit={e => { e.preventDefault(); create("/api/vendor/purchase-orders",
                    { ...poForm, project_id: poForm.project_id || null, total_amount: poForm.total_amount || null },
                    d => setPos(prev => [d as VendorPurchaseOrder, ...prev])); }}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                      {([["PO Number *","po_number"],["Vendor Name *","vendor_name"],["Description","description"]] as [string,string][]).map(([label,key]) => (
                        <label key={key} style={{ display:"flex",flexDirection:"column",gap:4,fontSize:13 }}>
                          {label}
                          <input value={(poForm as Record<string,string>)[key]}
                            onChange={e => setPoForm(p => ({...p,[key]:e.target.value}))} />
                        </label>
                      ))}
                      <label style={{ display:"flex",flexDirection:"column",gap:4,fontSize:13 }}>
                        Project
                        <select value={poForm.project_id} onChange={e => setPoForm(p => ({...p,project_id:e.target.value}))}>
                          <option value="">— none —</option>
                          {projOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </label>
                      <label style={{ display:"flex",flexDirection:"column",gap:4,fontSize:13 }}>
                        Total Amount ($)
                        <input type="number" step="0.01" value={poForm.total_amount} onChange={e => setPoForm(p => ({...p,total_amount:e.target.value}))} />
                      </label>
                      <label style={{ display:"flex",flexDirection:"column",gap:4,fontSize:13 }}>
                        Status
                        <select value={poForm.status} onChange={e => setPoForm(p => ({...p,status:e.target.value}))}>
                          {["pending","approved","rejected","cancelled"].map(s => <option key={s}>{s}</option>)}
                        </select>
                      </label>
                    </div>
                    <div style={{ marginTop:12,display:"flex",gap:8 }}>
                      <button type="submit" disabled={saving}>{saving?"Saving…":"Create PO"}</button>
                    </div>
                  </form>
                </div>
              )}
              <div className="card">
                {pos.length === 0 ? <p className="muted" style={{fontSize:13}}>No purchase orders yet.</p> : (
                  <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
                    <thead><tr style={{borderBottom:"2px solid #e2e8f0"}}>
                      {["PO Number","Vendor","Description","Amount","Status","Date"].map(h => (
                        <th key={h} style={{padding:"7px 10px",textAlign:"left",fontSize:11,fontWeight:700,textTransform:"uppercase",color:"#64748b"}}>{h}</th>
                      ))}
                    </tr></thead>
                    <tbody>{pos.map(p => (
                      <tr key={p.id} style={{borderBottom:"1px solid #f1f5f9"}}>
                        <td style={{padding:"8px 10px",fontWeight:600}}>{p.po_number}</td>
                        <td style={{padding:"8px 10px"}}>{p.vendor_name}</td>
                        <td style={{padding:"8px 10px",maxWidth:200,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{p.description || "—"}</td>
                        <td style={{padding:"8px 10px"}}>{fmt(p.total_amount)}</td>
                        <td style={{padding:"8px 10px"}}><Pill status={p.status}/></td>
                        <td style={{padding:"8px 10px",color:"#64748b"}}>{p.created_at?.slice(0,10)}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                )}
              </div>
            </>
          )}

          {/* ── Invoice Submissions ── */}
          {tab === "invoices" && (
            <>
              {showForm && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <h3 style={{ marginTop: 0, fontSize: 14 }}>New Invoice Submission</h3>
                  <form onSubmit={e => { e.preventDefault(); create("/api/vendor/invoice-submissions",
                    { ...invForm, project_id: invForm.project_id||null, purchase_order_id: invForm.purchase_order_id||null, amount: invForm.amount||null },
                    d => setInvoices(prev => [d as VendorInvoiceSubmission, ...prev])); }}>
                    <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12 }}>
                      {([["Invoice Number *","invoice_number"],["Vendor Name *","vendor_name"],["Notes","notes"]] as [string,string][]).map(([label,key]) => (
                        <label key={key} style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                          {label}<input value={(invForm as Record<string,string>)[key]} onChange={e => setInvForm(p => ({...p,[key]:e.target.value}))} />
                        </label>
                      ))}
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Linked PO
                        <select value={invForm.purchase_order_id} onChange={e => setInvForm(p => ({...p,purchase_order_id:e.target.value}))}>
                          <option value="">— none —</option>
                          {poOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Project
                        <select value={invForm.project_id} onChange={e => setInvForm(p => ({...p,project_id:e.target.value}))}>
                          <option value="">— none —</option>
                          {projOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Amount ($)<input type="number" step="0.01" value={invForm.amount} onChange={e => setInvForm(p => ({...p,amount:e.target.value}))} />
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Status
                        <select value={invForm.status} onChange={e => setInvForm(p => ({...p,status:e.target.value}))}>
                          {["submitted","approved","rejected","paid"].map(s => <option key={s}>{s}</option>)}
                        </select>
                      </label>
                    </div>
                    <div style={{marginTop:12,display:"flex",gap:8}}>
                      <button type="submit" disabled={saving}>{saving?"Saving…":"Submit Invoice"}</button>
                    </div>
                  </form>
                </div>
              )}
              <div className="card">
                {invoices.length === 0 ? <p className="muted" style={{fontSize:13}}>No invoice submissions yet.</p> : (
                  <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
                    <thead><tr style={{borderBottom:"2px solid #e2e8f0"}}>
                      {["Invoice #","Vendor","Amount","Linked PO","Status","Date"].map(h => (
                        <th key={h} style={{padding:"7px 10px",textAlign:"left",fontSize:11,fontWeight:700,textTransform:"uppercase",color:"#64748b"}}>{h}</th>
                      ))}
                    </tr></thead>
                    <tbody>{invoices.map(inv => (
                      <tr key={inv.id} style={{borderBottom:"1px solid #f1f5f9"}}>
                        <td style={{padding:"8px 10px",fontWeight:600}}>{inv.invoice_number}</td>
                        <td style={{padding:"8px 10px"}}>{inv.vendor_name}</td>
                        <td style={{padding:"8px 10px"}}>{fmt(inv.amount)}</td>
                        <td style={{padding:"8px 10px",color:"#64748b",fontSize:12}}>
                          {pos.find(p => p.id === inv.purchase_order_id)?.po_number || "—"}
                        </td>
                        <td style={{padding:"8px 10px"}}><Pill status={inv.status}/></td>
                        <td style={{padding:"8px 10px",color:"#64748b"}}>{inv.created_at?.slice(0,10)}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                )}
              </div>
            </>
          )}

          {/* ── Delivery Records ── */}
          {tab === "deliveries" && (
            <>
              {showForm && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <h3 style={{ marginTop: 0, fontSize: 14 }}>New Delivery Record</h3>
                  <form onSubmit={e => { e.preventDefault(); create("/api/vendor/delivery-records",
                    { ...delForm, project_id: delForm.project_id||null, purchase_order_id: delForm.purchase_order_id||null, received_at: delForm.received_at||null },
                    d => setDeliveries(prev => [d as VendorDeliveryRecord, ...prev])); }}>
                    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12}}>
                      {([["Ticket Number *","ticket_number"],["Vendor Name *","vendor_name"],["Destination","destination"]] as [string,string][]).map(([label,key]) => (
                        <label key={key} style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                          {label}<input value={(delForm as Record<string,string>)[key]} onChange={e => setDelForm(p => ({...p,[key]:e.target.value}))} />
                        </label>
                      ))}
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Linked PO
                        <select value={delForm.purchase_order_id} onChange={e => setDelForm(p => ({...p,purchase_order_id:e.target.value}))}>
                          <option value="">— none —</option>
                          {poOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Project
                        <select value={delForm.project_id} onChange={e => setDelForm(p => ({...p,project_id:e.target.value}))}>
                          <option value="">— none —</option>
                          {projOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Status
                        <select value={delForm.status} onChange={e => setDelForm(p => ({...p,status:e.target.value}))}>
                          {["in_transit","delivered","partial","rejected"].map(s => <option key={s}>{s}</option>)}
                        </select>
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Received At
                        <input type="datetime-local" value={delForm.received_at} onChange={e => setDelForm(p => ({...p,received_at:e.target.value}))} />
                      </label>
                    </div>
                    <div style={{marginTop:12,display:"flex",gap:8}}>
                      <button type="submit" disabled={saving}>{saving?"Saving…":"Record Delivery"}</button>
                    </div>
                  </form>
                </div>
              )}
              <div className="card">
                {deliveries.length === 0 ? <p className="muted" style={{fontSize:13}}>No delivery records yet.</p> : (
                  <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
                    <thead><tr style={{borderBottom:"2px solid #e2e8f0"}}>
                      {["Ticket #","Vendor","Destination","Linked PO","Status","Received"].map(h => (
                        <th key={h} style={{padding:"7px 10px",textAlign:"left",fontSize:11,fontWeight:700,textTransform:"uppercase",color:"#64748b"}}>{h}</th>
                      ))}
                    </tr></thead>
                    <tbody>{deliveries.map(d => (
                      <tr key={d.id} style={{borderBottom:"1px solid #f1f5f9"}}>
                        <td style={{padding:"8px 10px",fontWeight:600}}>{d.ticket_number}</td>
                        <td style={{padding:"8px 10px"}}>{d.vendor_name}</td>
                        <td style={{padding:"8px 10px"}}>{d.destination || "—"}</td>
                        <td style={{padding:"8px 10px",color:"#64748b",fontSize:12}}>
                          {pos.find(p => p.id === d.purchase_order_id)?.po_number || "—"}
                        </td>
                        <td style={{padding:"8px 10px"}}><Pill status={d.status}/></td>
                        <td style={{padding:"8px 10px",color:"#64748b"}}>{d.received_at?.slice(0,10) || "—"}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                )}
              </div>
            </>
          )}

          {/* ── Compliance Documents ── */}
          {tab === "compliance" && (
            <>
              {showForm && (
                <div className="card" style={{ marginBottom: 16 }}>
                  <h3 style={{ marginTop: 0, fontSize: 14 }}>New Compliance Document</h3>
                  <form onSubmit={e => { e.preventDefault(); create("/api/vendor/compliance-documents",
                    { ...compForm, project_id: compForm.project_id||null, expires_at: compForm.expires_at||null },
                    d => setCompliance(prev => [d as VendorComplianceDocument, ...prev])); }}>
                    <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12}}>
                      {([["Document Name *","document_name"],["Vendor Name *","vendor_name"],["Notes","notes"]] as [string,string][]).map(([label,key]) => (
                        <label key={key} style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                          {label}<input value={(compForm as Record<string,string>)[key]} onChange={e => setCompForm(p => ({...p,[key]:e.target.value}))} />
                        </label>
                      ))}
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Project
                        <select value={compForm.project_id} onChange={e => setCompForm(p => ({...p,project_id:e.target.value}))}>
                          <option value="">— none —</option>
                          {projOpts.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Status
                        <select value={compForm.status} onChange={e => setCompForm(p => ({...p,status:e.target.value}))}>
                          {["active","expired","pending","rejected"].map(s => <option key={s}>{s}</option>)}
                        </select>
                      </label>
                      <label style={{display:"flex",flexDirection:"column",gap:4,fontSize:13}}>
                        Expires At
                        <input type="date" value={compForm.expires_at} onChange={e => setCompForm(p => ({...p,expires_at:e.target.value}))} />
                      </label>
                    </div>
                    <div style={{marginTop:12,display:"flex",gap:8}}>
                      <button type="submit" disabled={saving}>{saving?"Saving…":"Add Document"}</button>
                    </div>
                  </form>
                </div>
              )}
              <div className="card">
                {compliance.length === 0 ? <p className="muted" style={{fontSize:13}}>No compliance documents yet.</p> : (
                  <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
                    <thead><tr style={{borderBottom:"2px solid #e2e8f0"}}>
                      {["Document","Vendor","Project","Status","Expires","Added"].map(h => (
                        <th key={h} style={{padding:"7px 10px",textAlign:"left",fontSize:11,fontWeight:700,textTransform:"uppercase",color:"#64748b"}}>{h}</th>
                      ))}
                    </tr></thead>
                    <tbody>{compliance.map(c => {
                      const isExpiring = c.expires_at && new Date(c.expires_at) <= new Date(Date.now() + 30*24*60*60*1000);
                      return (
                        <tr key={c.id} style={{borderBottom:"1px solid #f1f5f9",background:isExpiring?"#fff7ed":undefined}}>
                          <td style={{padding:"8px 10px",fontWeight:600}}>{c.document_name}</td>
                          <td style={{padding:"8px 10px"}}>{c.vendor_name}</td>
                          <td style={{padding:"8px 10px",color:"#64748b",fontSize:12}}>
                            {projects.find(p => p.id === c.project_id)?.project_name || "—"}
                          </td>
                          <td style={{padding:"8px 10px"}}><Pill status={c.status}/></td>
                          <td style={{padding:"8px 10px",color:isExpiring?"#d97706":"#64748b",fontWeight:isExpiring?700:400}}>
                            {c.expires_at?.slice(0,10) || "—"}{isExpiring?" ⚠️":""}
                          </td>
                          <td style={{padding:"8px 10px",color:"#64748b"}}>{c.created_at?.slice(0,10)}</td>
                        </tr>
                      );
                    })}</tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </>
      )}
    </AppShell>
  );
}
