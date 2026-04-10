"use client";
import { useEffect, useState } from "react";
import { getShelves, capture, detect, detectDebug, plan } from "../lib/api";
import type { Shelf, Waypoint, PlanMetrics } from "../lib/types";

type TaskType = "navigate" | "pick_place";

export default function PlanRunTab() {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [taskType, setTaskType] = useState<TaskType>("pick_place");
  const [src, setSrc] = useState<string>("");
  const [dst, setDst] = useState<string>("");
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [waypoints, setWaypoints] = useState<Waypoint[]>([]);
  const [metrics, setMetrics] = useState<PlanMetrics | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const data = await getShelves();
        setShelves(data.shelves);
        if (data.shelves.length >= 1) setSrc(data.shelves[0].id);
        if (data.shelves.length >= 2) setDst(data.shelves[1].id);
      } catch (e) { setMessage(String(e)); }
    })();
  }, []);

  // Keep source and destination different whenever the lists change.
  useEffect(() => {
    if (src === dst && shelves.length >= 2) {
      const other = shelves.find(s => s.id !== src);
      if (other) setDst(other.id);
    }
  }, [src, dst, shelves]);

  const handleCapture = async () => {
    try {
      const r = await capture();
      setImageB64(r.image_base64);
      setWaypoints([]);
      setMetrics(null);
    } catch (e) { setMessage(String(e)); }
  };

  const handleDetect = async () => {
    try {
      const r = await detect();
      setImageB64(r.annotated_image_base64);
      setMessage(r.robot_pose ? `Robot at (${r.robot_pose.x_m.toFixed(2)}, ${r.robot_pose.y_m.toFixed(2)}) @ ${r.robot_pose.heading_deg.toFixed(0)} deg` : "Markers not found");
    } catch (e) { setMessage(String(e)); }
  };

  const handleDetectDebug = async () => {
    try {
      const r = await detectDebug();
      setImageB64(r.mask_overlay_base64);
      setWaypoints([]);
      setMetrics(null);
      const frontOk = r.front_largest_area_px >= r.min_marker_area_px;
      const backOk = r.back_largest_area_px >= r.min_marker_area_px;
      setMessage(
        `Front (${r.front_color_name}): largest blob ${r.front_largest_area_px}px ${frontOk ? "✓" : "✗ (need ≥" + r.min_marker_area_px + ")"}. ` +
        `Back (${r.back_color_name}): largest blob ${r.back_largest_area_px}px ${backOk ? "✓" : "✗ (need ≥" + r.min_marker_area_px + ")"}.`,
      );
    } catch (e) { setMessage(String(e)); }
  };

  const handlePlan = async () => {
    try {
      const r = await plan({
        task: taskType,
        source_shelf_id: taskType === "pick_place" ? src : undefined,
        destination_shelf_id: dst,
      });
      setImageB64(r.annotated_image_base64);
      setWaypoints(r.waypoints);
      setMetrics(r.metrics);
      setMessage("");
    } catch (e) { setMessage(String(e)); }
  };

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-3 space-y-3">
        <label className="block">
          <span className="text-white/60 text-sm">Task</span>
          <select value={taskType} onChange={e => setTaskType(e.target.value as TaskType)} className="w-full bg-black border border-white/20 px-2 py-1">
            <option value="navigate">Navigate</option>
            <option value="pick_place">Pick &amp; Place</option>
          </select>
        </label>
        {taskType === "pick_place" && (
          <label className="block">
            <span className="text-white/60 text-sm">Source shelf</span>
            <select value={src} onChange={e => setSrc(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
              {shelves.filter(s => s.id !== dst).map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
            </select>
          </label>
        )}
        <label className="block">
          <span className="text-white/60 text-sm">Destination shelf</span>
          <select value={dst} onChange={e => setDst(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
            {shelves.filter(s => taskType !== "pick_place" || s.id !== src).map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
          </select>
        </label>
      </div>

      <div className="col-span-6 space-y-2">
        <div className="flex gap-2">
          <button type="button" onClick={handleCapture} className="px-3 py-1 bg-gray-600 rounded">Capture</button>
          <button type="button" onClick={handleDetect} className="px-3 py-1 bg-blue-600 rounded">Detect</button>
          <button type="button" onClick={handleDetectDebug} className="px-3 py-1 bg-amber-600 rounded" title="Show raw color masks for tuning">Debug masks</button>
          <button type="button" onClick={handlePlan} className="px-3 py-1 bg-green-600 rounded">Plan</button>
        </div>
        {imageB64 && (
          <img src={`data:image/png;base64,${imageB64}`} alt="vision feed" className="w-full border border-white/20" />
        )}
        {message && <div className="text-sm text-white/80">{message}</div>}
      </div>

      <div className="col-span-3 space-y-2">
        <div className="font-bold">Waypoints</div>
        <ol className="text-sm space-y-1 max-h-96 overflow-auto">
          {waypoints.map((w, i) => (
            <li key={i} className="border-l-2 border-blue-400 pl-2">
              <div className="text-white">{w.type}</div>
              {w.type === "turn" && <div className="text-white/60">{w.target_heading_deg?.toFixed(0)} deg</div>}
              {w.type === "drive" && <div className="text-white/60">{w.distance_m?.toFixed(2)} m</div>}
              {(w.type === "grab" || w.type === "place") && <div className="text-white/60">{w.shelf_id}</div>}
            </li>
          ))}
        </ol>
        {metrics && (
          <div className="text-sm pt-2 border-t border-white/10">
            <div>Total distance: {metrics.total_distance_m.toFixed(2)} m</div>
            <div>Est. time: {metrics.estimated_time_s.toFixed(1)} s</div>
          </div>
        )}
        <button type="button" disabled className="px-3 py-1 bg-gray-700 rounded opacity-50" title="Hardware integration pending">
          Execute
        </button>
      </div>
    </div>
  );
}
