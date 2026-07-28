"use client";

import React from "react";
import { useEffect, useMemo, useState } from "react";

import {
  MaterialDensityPreset,
  TicketApiError,
  TicketQuantityCalculationResponse,
  calculateTicketQuantities,
  listMaterialDensityPresets,
  upsertMaterialDensityPreset,
} from "@/lib/tickets";

const DEFAULT_DIRT_PRESET_ID = "__default_dirt_preset__";
const DEFAULT_DIRT_MATERIAL = "Dirt";
const DEFAULT_DIRT_DENSITY = "1.20";

// Comprehensive materials library organized by category with preset densities (tons per cubic yard)
const MATERIALS_BY_CATEGORY = {
  "Soil & Earth": [
    { name: "Topsoil", density: "1.30" },
    { name: "Fill dirt", density: "1.20" },
    { name: "Common fill", density: "1.25" },
    { name: "Structural fill", density: "1.35" },
    { name: "Select fill", density: "1.28" },
    { name: "Clay", density: "1.40" },
    { name: "Sand", density: "1.40" },
    { name: "Silt", density: "1.28" },
    { name: "Wet soil", density: "1.50" },
    { name: "Excavated dirt", density: "1.20" },
  ],
  "Stone & Aggregate": [
    { name: "ABC stone (crusher run)", density: "1.50" },
    { name: "Crushed stone", density: "1.50" },
    { name: "Gravel", density: "1.45" },
    { name: "Washed stone", density: "1.55" },
    { name: "Pea gravel", density: "1.40" },
    { name: "Riprap", density: "1.60" },
    { name: "#57 stone", density: "1.50" },
    { name: "#67 stone", density: "1.48" },
    { name: "#78 stone", density: "1.45" },
    { name: "Stone dust", density: "1.35" },
    { name: "Recycled concrete aggregate", density: "1.45" },
  ],
  "Road & Paving": [
    { name: "Asphalt", density: "1.45" },
    { name: "Reclaimed asphalt pavement (RAP)", density: "1.40" },
    { name: "Base course", density: "1.50" },
    { name: "Subbase material", density: "1.48" },
    { name: "Milling material", density: "1.42" },
    { name: "Concrete", density: "2.40" },
    { name: "Flowable fill", density: "1.60" },
  ],
  "Clearing & Demolition": [
    { name: "Mulch", density: "0.75" },
    { name: "Brush", density: "0.40" },
    { name: "Logs", density: "0.60" },
    { name: "Stumps", density: "0.85" },
    { name: "Vegetative debris", density: "0.50" },
    { name: "Concrete debris", density: "2.20" },
    { name: "Asphalt debris", density: "1.40" },
    { name: "Brick", density: "1.80" },
    { name: "Block", density: "1.85" },
    { name: "Mixed construction debris", density: "1.35" },
  ],
  "Utility & Drainage": [
    { name: "Pipe bedding stone", density: "1.50" },
    { name: "Trench backfill", density: "1.35" },
    { name: "Drainage stone", density: "1.50" },
    { name: "Sand bedding", density: "1.40" },
  ],
  "Landscaping": [
    { name: "Landscape soil", density: "1.32" },
    { name: "Compost", density: "0.85" },
  ],
  "Other": [
    { name: "Salt", density: "1.30" },
    { name: "Lime", density: "1.25" },
    { name: "Scrap metal", density: "2.50" },
  ],
} as const;

// Flattened array for backward compatibility
const COMMON_MATERIALS = Object.values(MATERIALS_BY_CATEGORY).flat();

const TRUCK_TYPE_OPTIONS = [
  { value: "", label: "Select truck type...", capacity: "" },
  { value: "tandem", label: "Tandem", capacity: "18" },
  { value: "triaxle", label: "Triaxle", capacity: "22" },
  { value: "quad", label: "Quad-Axle", capacity: "22" },
  { value: "quint", label: "Quint-Axle", capacity: "26" },
  { value: "custom", label: "Custom capacity", capacity: "" },
] as const;

type TicketCalculatorPanelProps = {
  title?: string;
  prefill?: {
    materialName?: string;
    grossWeightLbs?: string;
    tareWeightLbs?: string;
    netWeightLbs?: string;
    numberOfLoads?: string;
  } | null;
  onApply: (payload: {
    material: string;
    weight: string;
    tons: string;
    volumeYards: string;
    selectedTotalCost: string;
  }) => void;
};

export default function TicketCalculatorPanel({
  title = "Ticket calculator",
  prefill = null,
  onApply,
}: TicketCalculatorPanelProps) {
  const [materialName, setMaterialName] = useState("");
  const [grossWeightLbs, setGrossWeightLbs] = useState("");
  const [tareWeightLbs, setTareWeightLbs] = useState("");
  const [netWeightLbs, setNetWeightLbs] = useState("");
  const [numberOfLoads, setNumberOfLoads] = useState("1");
  const [truckType, setTruckType] = useState("");
  const [truckCapacityTons, setTruckCapacityTons] = useState("");
  const [density, setDensity] = useState("");
  const [ratePerTon, setRatePerTon] = useState("");
  const [ratePerCubicYard, setRatePerCubicYard] = useState("");
  const [ratePerLoad, setRatePerLoad] = useState("");
  const [selectedPresetId, setSelectedPresetId] = useState("");
  const [presets, setPresets] = useState<MaterialDensityPreset[]>([]);
  const [result, setResult] = useState<TicketQuantityCalculationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingPreset, setSavingPreset] = useState(false);
  const [message, setMessage] = useState("");
  const [presetLoadError, setPresetLoadError] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<keyof typeof MATERIALS_BY_CATEGORY | "">("Soil & Earth");

  const sortedPresets = useMemo(
    () => [...presets].sort((a, b) => a.material_name.localeCompare(b.material_name)),
    [presets]
  );

  const selectablePresets = useMemo(() => {
    const hasDirtPreset = sortedPresets.some(
      (preset) => preset.material_name.trim().toLowerCase() === DEFAULT_DIRT_MATERIAL.toLowerCase()
    );
    if (hasDirtPreset) {
      return sortedPresets;
    }

    return [
      {
        id: DEFAULT_DIRT_PRESET_ID,
        tenant_id: "",
        material_name: DEFAULT_DIRT_MATERIAL,
        density_tons_per_cubic_yard: DEFAULT_DIRT_DENSITY,
        created_by: "",
        created_at: "",
        updated_at: "",
      },
      ...sortedPresets,
    ];
  }, [sortedPresets]);

  useEffect(() => {
    void (async () => {
      try {
        const data = await listMaterialDensityPresets();
        setPresets(data);
        setPresetLoadError(false);
      } catch {
        setPresets([]);
        setPresetLoadError(true);
      }
    })();
  }, []);

  // Auto-calculate net weight when both gross and tare are provided
  const autoNetWeight = (() => {
    const g = parseFloat(grossWeightLbs);
    const t = parseFloat(tareWeightLbs);
    if (!isNaN(g) && !isNaN(t) && g >= t) {
      return String(Math.round(g - t));
    }
    return "";
  })();

  const displayNetWeight = autoNetWeight || netWeightLbs;

  useEffect(() => {
    if (!prefill) {
      return;
    }
    if (typeof prefill.materialName === "string") {
      setMaterialName(prefill.materialName);
    }
    if (typeof prefill.grossWeightLbs === "string") {
      setGrossWeightLbs(prefill.grossWeightLbs);
    }
    if (typeof prefill.tareWeightLbs === "string") {
      setTareWeightLbs(prefill.tareWeightLbs);
    }
    if (typeof prefill.netWeightLbs === "string") {
      setNetWeightLbs(prefill.netWeightLbs);
    }
    if (typeof prefill.numberOfLoads === "string") {
      setNumberOfLoads(prefill.numberOfLoads);
    }
  }, [prefill]);

  useEffect(() => {
    if (selectedPresetId) {
      return;
    }

    const dirtPreset = selectablePresets.find(
      (preset) => preset.material_name.trim().toLowerCase() === DEFAULT_DIRT_MATERIAL.toLowerCase()
    );
    if (!dirtPreset) {
      return;
    }

    setSelectedPresetId(dirtPreset.id);
    setMaterialName(dirtPreset.material_name);
    if (!density.trim()) {
      setDensity(dirtPreset.density_tons_per_cubic_yard || DEFAULT_DIRT_DENSITY);
    }
  }, [density, selectablePresets, selectedPresetId]);

  async function savePreset(): Promise<void> {
    const trimmedMaterial = materialName.trim();
    const trimmedDensity = density.trim();
    if (!trimmedMaterial || !trimmedDensity) {
      setMessage("Material and density are required to save a preset.");
      return;
    }

    setSavingPreset(true);
    setMessage("");
    try {
      const saved = await upsertMaterialDensityPreset(trimmedMaterial, trimmedDensity);
      setPresets((prev) => {
        const withoutExisting = prev.filter(
          (item) => item.material_name.toLowerCase() !== saved.material_name.toLowerCase()
        );
        return [...withoutExisting, saved];
      });
      setSelectedPresetId(saved.id);
      setMessage(`Saved density preset for ${saved.material_name}.`);
    } catch (err) {
      if (err instanceof TicketApiError) {
        setMessage(err.detail);
      } else {
        setMessage("Unable to save material density preset.");
      }
    } finally {
      setSavingPreset(false);
    }
  }

  async function runCalculation(): Promise<void> {
    setLoading(true);
    setMessage("");
    try {
      const effectiveNetWeight = autoNetWeight || netWeightLbs.trim();
      const payload = {
        material_name: materialName.trim() || undefined,
        gross_weight_lbs: grossWeightLbs.trim() || undefined,
        tare_weight_lbs: tareWeightLbs.trim() || undefined,
        net_weight_lbs: effectiveNetWeight || undefined,
        number_of_loads: numberOfLoads.trim() ? Number(numberOfLoads) : undefined,
        truck_type: truckType || undefined,
        truck_capacity_tons: truckCapacityTons.trim() || undefined,
        material_density_tons_per_cubic_yard: density.trim() || undefined,
        rate_per_ton: ratePerTon.trim() || undefined,
        rate_per_cubic_yard: ratePerCubicYard.trim() || undefined,
        rate_per_load: ratePerLoad.trim() || undefined,
      };

      const response = await calculateTicketQuantities(payload);
      setResult(response);
    } catch (err) {
      if (err instanceof TicketApiError) {
        setMessage(err.detail);
      } else {
        setMessage("Unable to run ticket calculation.");
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  function applyToTicketForm(): void {
    if (!result || !result.net_weight_lbs || !result.net_tons) {
      setMessage("Run a valid calculation first.");
      return;
    }

    onApply({
      material: materialName.trim() || result.resolved_material_name || "",
      weight: result.net_weight_lbs,
      tons: result.net_tons,
      volumeYards: result.estimated_cubic_yards || "",
      selectedTotalCost: result.selected_total_cost || "",
    });
    setMessage("Calculation outputs applied to ticket form.");
  }

  return (
    <div className="card">
      <div className="section-header">
        <h3>{title}</h3>
        <button onClick={() => void runCalculation()} disabled={loading}>
          {loading ? "Calculating..." : "Run ticket calculation"}
        </button>
      </div>

      {/* Quick Material Selection by Category */}
      <div style={{ marginBottom: "20px", padding: "12px", backgroundColor: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
        <p style={{ margin: "0 0 12px 0", fontSize: "14px", fontWeight: "600", color: "#334155" }}>
          📦 Quick material selection (auto-fills density):
        </p>
        
        {/* Category Tabs */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "12px" }}>
          {(Object.keys(MATERIALS_BY_CATEGORY) as Array<keyof typeof MATERIALS_BY_CATEGORY>).map((category) => (
            <button
              key={category}
              onClick={() => setSelectedCategory(category)}
              style={{
                padding: "8px 12px",
                backgroundColor: selectedCategory === category ? "#0ea5e9" : "#cbd5e1",
                color: selectedCategory === category ? "white" : "#1e293b",
                border: "none",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: selectedCategory === category ? "600" : "500",
                transition: "all 200ms",
                boxShadow: selectedCategory === category ? "0 2px 8px rgba(6,182,212,0.3)" : "none",
              }}
              onMouseEnter={(e) => {
                if (selectedCategory !== category) {
                  (e.target as HTMLButtonElement).style.backgroundColor = "#94a3b8";
                }
              }}
              onMouseLeave={(e) => {
                if (selectedCategory !== category) {
                  (e.target as HTMLButtonElement).style.backgroundColor = "#cbd5e1";
                }
              }}
            >
              {category}
            </button>
          ))}
        </div>

        {/* Materials in Selected Category */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "8px" }}>
          {selectedCategory && MATERIALS_BY_CATEGORY[selectedCategory]?.map((material) => (
            <button
              key={material.name}
              onClick={() => {
                setMaterialName(material.name);
                setDensity(material.density);
                setSelectedPresetId("");
              }}
              style={{
                padding: "10px 12px",
                backgroundColor: materialName === material.name ? "#10b981" : "#e0f2fe",
                color: materialName === material.name ? "white" : "#0369a1",
                border: materialName === material.name ? "2px solid #059669" : "1px solid #06b6d4",
                borderRadius: "6px",
                cursor: "pointer",
                fontSize: "13px",
                fontWeight: materialName === material.name ? "600" : "500",
                transition: "all 200ms",
                boxShadow: materialName === material.name ? "0 4px 12px rgba(16,185,129,0.3)" : "none",
              }}
              onMouseEnter={(e) => {
                if (materialName !== material.name) {
                  (e.target as HTMLButtonElement).style.backgroundColor = "#cffafe";
                  (e.target as HTMLButtonElement).style.boxShadow = "0 2px 8px rgba(6,182,212,0.2)";
                }
              }}
              onMouseLeave={(e) => {
                if (materialName !== material.name) {
                  (e.target as HTMLButtonElement).style.backgroundColor = "#e0f2fe";
                  (e.target as HTMLButtonElement).style.boxShadow = "none";
                }
              }}
              title={`${material.name} - Density: ${material.density} tons/yard³`}
            >
              {material.name}
              <div style={{ fontSize: "11px", opacity: "0.8", marginTop: "2px" }}>
                {material.density} t/yd³
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="form-grid replay-controls-grid">
        <label>
          Material
          <input
            type="text"
            value={materialName}
            onChange={(e) => setMaterialName(e.target.value)}
            placeholder="Aggregate"
          />
        </label>
        <label>
          Material preset
          <select
            value={selectedPresetId}
            onChange={(e) => {
              setSelectedPresetId(e.target.value);
              const selected = selectablePresets.find((preset) => preset.id === e.target.value);
              if (!selected) {
                return;
              }
              setMaterialName(selected.material_name);
              setDensity(selected.density_tons_per_cubic_yard || DEFAULT_DIRT_DENSITY);
            }}
          >
            <option value="">Select preset...</option>
            {selectablePresets.map((preset) => (
              <option key={preset.id} value={preset.id}>
                {preset.material_name} ({preset.density_tons_per_cubic_yard})
              </option>
            ))}
          </select>
        </label>
        {presetLoadError ? (
          <p className="metric-note">Material presets failed to load. Re-authenticate if your session expired.</p>
        ) : null}
        <label>
          Truck type
          <select
            value={truckType}
            onChange={(e) => {
              const selected = TRUCK_TYPE_OPTIONS.find((o) => o.value === e.target.value);
              setTruckType(e.target.value);
              if (selected && selected.capacity) {
                setTruckCapacityTons(selected.capacity);
              } else if (e.target.value === "custom") {
                setTruckCapacityTons("");
              }
            }}
          >
            {TRUCK_TYPE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}{o.capacity ? ` (~${o.capacity} tons)` : ""}</option>
            ))}
          </select>
        </label>
        <label>
          Truck capacity (tons / load)
          <input
            type="number"
            value={truckCapacityTons}
            onChange={(e) => setTruckCapacityTons(e.target.value)}
            placeholder="Auto from truck type"
          />
        </label>
        <label>
          Gross weight (lbs)
          <input type="number" value={grossWeightLbs} onChange={(e) => setGrossWeightLbs(e.target.value)} />
        </label>
        <label>
          Tare weight (lbs)
          <input type="number" value={tareWeightLbs} onChange={(e) => setTareWeightLbs(e.target.value)} />
        </label>
        <label>
          Net weight (lbs){autoNetWeight ? " (auto)" : ""}
          <input
            type="number"
            value={displayNetWeight}
            readOnly={!!autoNetWeight}
            onChange={(e) => { if (!autoNetWeight) setNetWeightLbs(e.target.value); }}
            style={autoNetWeight ? { background: "#f0f4f8", cursor: "default" } : undefined}
            placeholder="Auto from gross − tare"
          />
        </label>
        <label>
          Number of loads
          <input type="number" min={1} value={numberOfLoads} onChange={(e) => setNumberOfLoads(e.target.value)} />
        </label>
        <label>
          Density (tons / cubic yard)
          <input type="number" value={density} onChange={(e) => setDensity(e.target.value)} />
        </label>
        <label>
          Rate per ton
          <input type="number" value={ratePerTon} onChange={(e) => setRatePerTon(e.target.value)} />
        </label>
        <label>
          Rate per cubic yard
          <input type="number" value={ratePerCubicYard} onChange={(e) => setRatePerCubicYard(e.target.value)} />
        </label>
        <label>
          Rate per load
          <input type="number" value={ratePerLoad} onChange={(e) => setRatePerLoad(e.target.value)} />
        </label>
      </div>

      <div className="replay-action-row">
        <button onClick={() => void savePreset()} disabled={savingPreset}>
          {savingPreset ? "Saving preset..." : "Save density preset"}
        </button>
        <button onClick={applyToTicketForm} disabled={!result}>
          Apply outputs to ticket form
        </button>
      </div>

      {result ? (
        <div className="token-state-table-wrap">
          {result.weight_method ? (
            <p className="metric-note">
              <strong>
                {result.weight_method === "actual" ? "✓ Actual weight (scale)" : "~ Estimated weight (truck capacity × loads)"}
              </strong>
              {result.resolved_truck_type
                ? ` — ${result.resolved_truck_type.charAt(0).toUpperCase() + result.resolved_truck_type.slice(1)} (${result.resolved_truck_capacity_tons} tons/load)`
                : ""}
            </p>
          ) : null}
          <table className="token-state-table">
            <thead>
              <tr>
                <th>Net lbs</th>
                <th>Net tons / load</th>
                <th>Total tons</th>
                <th>Total yards</th>
                <th>Load count</th>
                <th>Yards/load</th>
                <th>Selected cost</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{result.net_weight_lbs || "n/a"}</td>
                <td>{result.net_tons || "n/a"}</td>
                <td>
                  {result.total_tons || "n/a"}
                  {result.weight_method === "estimated" ? " (est)" : result.weight_method === "actual" ? " (actual)" : ""}
                </td>
                <td>
                  {result.total_cubic_yards || result.estimated_cubic_yards || "n/a"}
                  {result.weight_method === "estimated" ? " (est)" : ""}
                </td>
                <td>{result.estimated_load_count || "n/a"}</td>
                <td>{result.cubic_yards_per_load || "n/a"}</td>
                <td>
                  {result.selected_total_cost || "n/a"}
                  {result.selected_cost_method ? ` (${result.selected_cost_method})` : ""}
                </td>
              </tr>
            </tbody>
          </table>
          {result.resolved_density_source ? (
            <p className="metric-note">
              Density source: {result.resolved_density_source}
              {result.resolved_material_name ? ` (${result.resolved_material_name})` : ""}
            </p>
          ) : null}
          {result.assumptions.length > 0 ? (
            <p className="metric-note">Assumptions: {result.assumptions.join(" | ")}</p>
          ) : null}
        </div>
      ) : null}

      {message ? <p className="metric-note">{message}</p> : null}
    </div>
  );
}
