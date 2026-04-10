"use client";
import { useEffect, useState } from "react";
import { getShelves, saveShelves, getSettings } from "../lib/api";
import type { Shelf, Settings } from "../lib/types";

const PX_PER_M = 200;

function emptyShelf(id: string): Shelf {
  return {
    id,
    x_m: 1.25, y_m: 1.25, width_m: 0.5, length_m: 0.5, rotation_deg: 0,
    approach_point: { x_m: 0.75, y_m: 1.25, heading_deg: 0 },
  };
}

export default function LayoutEditorTab() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setSettings(await getSettings());
        const data = await getShelves();
        setShelves(data.shelves);
      } catch (e) { setMessage(String(e)); }
    })();
  }, []);

  const selected = shelves.find(s => s.id === selectedId) ?? null;

  const updateSelected = (patch: Partial<Shelf>) => {
    if (!selected) return;
    setShelves(shelves.map(s => s.id === selected.id ? { ...s, ...patch } : s));
    setDirty(true);
  };

  const updateApproach = (patch: Partial<Shelf["approach_point"]>) => {
    if (!selected) return;
    setShelves(shelves.map(s =>
      s.id === selected.id
        ? { ...s, approach_point: { ...s.approach_point, ...patch } }
        : s
    ));
    setDirty(true);
  };

  const addShelf = () => {
    const id = `shelf_${String.fromCharCode(65 + shelves.length)}`;
    setShelves([...shelves, emptyShelf(id)]);
    setSelectedId(id);
    setDirty(true);
  };

  const deleteSelected = () => {
    if (!selected) return;
    setShelves(shelves.filter(s => s.id !== selected.id));
    setSelectedId(null);
    setDirty(true);
  };

  const save = async () => {
    try {
      await saveShelves(shelves);
      setDirty(false);
      setMessage("Saved.");
    } catch (e) { setMessage(`Save failed: ${e}`); }
  };

  if (!settings) return <div>Loading…</div>;

  const W = settings.workspace.width_m * PX_PER_M;
  const H = settings.workspace.height_m * PX_PER_M;

  return (
    <div className="flex gap-6">
      <div>
        <div className="flex gap-2 mb-2">
          <button onClick={addShelf} className="px-3 py-1 bg-blue-600 rounded">Add Shelf</button>
          <button onClick={deleteSelected} disabled={!selected} className="px-3 py-1 bg-red-600 rounded disabled:opacity-50">Delete</button>
          <button onClick={save} disabled={!dirty} className="px-3 py-1 bg-green-600 rounded disabled:opacity-50">
            Save {dirty && "*"}
          </button>
        </div>
        <svg
          width={W}
          height={H}
          viewBox={`0 ${-H} ${W} ${H}`}
          className="border border-white/20 bg-black"
        >
          {Array.from({ length: Math.ceil(settings.workspace.width_m / 0.5) + 1 }).map((_, i) => (
            <line key={`v${i}`} x1={i * 0.5 * PX_PER_M} y1={-H} x2={i * 0.5 * PX_PER_M} y2={0} stroke="#222" />
          ))}
          {Array.from({ length: Math.ceil(settings.workspace.height_m / 0.5) + 1 }).map((_, i) => (
            <line key={`h${i}`} x1={0} y1={-i * 0.5 * PX_PER_M} x2={W} y2={-i * 0.5 * PX_PER_M} stroke="#222" />
          ))}
          {shelves.map(s => (
            <g key={s.id}
              transform={`translate(${s.x_m * PX_PER_M} ${-s.y_m * PX_PER_M}) rotate(${-s.rotation_deg})`}
              onClick={() => setSelectedId(s.id)}
              className="cursor-pointer"
            >
              <rect
                x={-s.width_m * PX_PER_M / 2}
                y={-s.length_m * PX_PER_M / 2}
                width={s.width_m * PX_PER_M}
                height={s.length_m * PX_PER_M}
                fill={selectedId === s.id ? "#1e3a8a" : "#334155"}
                stroke="#60a5fa"
              />
              <text x={0} y={0} fill="white" fontSize={12} textAnchor="middle" alignmentBaseline="middle">
                {s.id}
              </text>
            </g>
          ))}
          {shelves.map(s => {
            const ap = s.approach_point;
            const tipX = ap.x_m + 0.15 * Math.cos((ap.heading_deg * Math.PI) / 180);
            const tipY = ap.y_m + 0.15 * Math.sin((ap.heading_deg * Math.PI) / 180);
            return (
              <line
                key={`ap-${s.id}`}
                x1={ap.x_m * PX_PER_M} y1={-ap.y_m * PX_PER_M}
                x2={tipX * PX_PER_M} y2={-tipY * PX_PER_M}
                stroke="#facc15" strokeWidth={3}
              />
            );
          })}
        </svg>
      </div>

      {selected && (
        <div className="w-64 space-y-2 text-sm">
          <div className="font-bold">{selected.id}</div>
          {(["x_m", "y_m", "width_m", "length_m", "rotation_deg"] as const).map(field => (
            <label key={field} className="block">
              <span className="text-white/60">{field}</span>
              <input
                type="number" step="0.01"
                value={selected[field]}
                onChange={e => updateSelected({ [field]: parseFloat(e.target.value) } as Partial<Shelf>)}
                className="w-full bg-black border border-white/20 px-2 py-1"
              />
            </label>
          ))}
          <div className="pt-2 border-t border-white/10">Approach point</div>
          {(["x_m", "y_m", "heading_deg"] as const).map(field => (
            <label key={field} className="block">
              <span className="text-white/60">{field}</span>
              <input
                type="number" step="0.01"
                value={selected.approach_point[field]}
                onChange={e => updateApproach({ [field]: parseFloat(e.target.value) })}
                className="w-full bg-black border border-white/20 px-2 py-1"
              />
            </label>
          ))}
        </div>
      )}

      {message && <div className="ml-auto text-sm text-white/80">{message}</div>}
    </div>
  );
}
