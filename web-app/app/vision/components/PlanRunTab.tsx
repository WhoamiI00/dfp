"use client";
import { useEffect, useRef, useState } from "react";
import {
  getShelves, capture, detect, plan, executePlan, sendRobotCommand,
  getRobotMode, setRobotMode, executeStream, abortExecute,
  autoDetectShelves,
  type AckEventData,
} from "../lib/api";
import type { Shelf, Waypoint, PlanMetrics } from "../lib/types";

type TaskType = "navigate" | "pick_place";

type LoopLogEntry = {
  step: number;
  cmd: string;
  reply: string;
  elapsed_ms: number;
  ok: boolean;
};

export default function PlanRunTab() {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [taskType, setTaskType] = useState<TaskType>("pick_place");
  const [src, setSrc] = useState<string>("");
  const [dst, setDst] = useState<string>("");
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [waypoints, setWaypoints] = useState<Waypoint[]>([]);
  const [metrics, setMetrics] = useState<PlanMetrics | null>(null);
  const [message, setMessage] = useState("");
  const [executing, setExecuting] = useState(false);

  const [simMode, setSimMode] = useState<boolean>(false);
  const [streaming, setStreaming] = useState(false);
  const [loopLog, setLoopLog] = useState<LoopLogEntry[]>([]);
  const streamAbortRef = useRef<AbortController | null>(null);

  // Live preview: poll /api/capture every LIVE_PREVIEW_MS ms and overwrite
  // the displayed image. Uses fresh=false on the backend so no drain cost.
  // Auto-pauses while a closed-loop run is streaming (which pushes its own
  // frames) or while the user is sending a manual command.
  const [livePreview, setLivePreview] = useState(false);
  const LIVE_PREVIEW_MS = 400;

  useEffect(() => {
    (async () => {
      try {
        const data = await getShelves();
        setShelves(data.shelves);
        if (data.shelves.length >= 1) setSrc(data.shelves[0].id);
        if (data.shelves.length >= 2) setDst(data.shelves[1].id);
      } catch (e) { setMessage(String(e)); }
      try {
        const m = await getRobotMode();
        setSimMode(m.sim);
      } catch { /* non-fatal: backend might be older */ }
    })();
  }, []);

  // Keep source and destination different whenever the lists change.
  useEffect(() => {
    if (src === dst && shelves.length >= 2) {
      const other = shelves.find(s => s.id !== src);
      if (other) setDst(other.id);
    }
  }, [src, dst, shelves]);

  // Live-preview poller. Pauses during streaming/manual to avoid stomping on
  // the SSE-driven frame or racing with manual commands.
  useEffect(() => {
    if (!livePreview || streaming || executing) return;
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      try {
        const r = await capture();
        if (!cancelled) setImageB64(r.image_base64);
      } catch {
        // Network blip — silently skip; the next tick will retry.
      }
    };
    tick();  // fire one immediately so the user sees the preview start fast
    const id = setInterval(tick, LIVE_PREVIEW_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [livePreview, streaming, executing]);

  const handleToggleSim = async () => {
    try {
      const m = await setRobotMode(!simMode);
      setSimMode(m.sim);
      setMessage(m.sim ? "Sim mode ON — fake serial, no Bluetooth." : "Live BT mode — commands go to the robot.");
    } catch (e) { setMessage(String(e)); }
  };

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

  const handleDetectShelves = async () => {
    try {
      setMessage("Detecting shelves…");
      // Preview-only: do NOT overwrite the saved layout. The seeded production
      // shelves (with correct stacked-floor approach points) stay intact, and
      // the user sees what auto-detect would propose. Use the Layout Editor
      // tab if you actually want to commit detected positions.
      const r = await autoDetectShelves({ persist: false });
      setImageB64(r.annotated_image_base64);
      setWaypoints([]);
      setMetrics(null);
      setMessage(
        r.shelves.length === 0
          ? "No shelf markers detected — using saved layout for planning."
          : `Detected ${r.shelves.length} shelf marker${r.shelves.length === 1 ? "" : "s"} (preview only). Saved layout unchanged.`,
      );
    } catch (e) {
      // Detection failure is non-fatal — Plan can still use the saved layout.
      setMessage(`Detect shelves failed (saved layout still usable): ${e}`);
    }
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

  const handleExecute = async () => {
    if (!dst) return;
    setExecuting(true);
    setMessage("Executing… robot is moving, do not interrupt.");
    try {
      const r = await executePlan({
        task: taskType,
        source_shelf_id: taskType === "pick_place" ? src : undefined,
        destination_shelf_id: dst,
      });
      if (r.ok) {
        setMessage(`Executed ${r.chars_sent} commands (${r.sequence}).`);
      } else {
        setMessage(`Execution failed after ${r.chars_sent} commands: ${r.error ?? "unknown error"}`);
      }
    } catch (e) {
      setMessage(String(e));
    } finally {
      setExecuting(false);
    }
  };

  const handleExecuteClosedLoop = async () => {
    if (!dst || streaming) return;
    setStreaming(true);
    setLoopLog([]);
    setWaypoints([]);
    setMetrics(null);
    setMessage("Closed-loop running — capturing and replanning every step.");

    const ctrl = new AbortController();
    streamAbortRef.current = ctrl;

    try {
      const stream = executeStream({
        task: taskType,
        source_shelf_id: taskType === "pick_place" ? src : undefined,
        destination_shelf_id: dst,
        signal: ctrl.signal,
      });
      for await (const ev of stream) {
        if (ev.event === "step") {
          setImageB64(ev.data.frame_b64);
          if (ev.data.next_cmd) {
            setMessage(`Step ${ev.data.step_idx}: pose (${ev.data.pose?.x_m.toFixed(2)}, ${ev.data.pose?.y_m.toFixed(2)}) @ ${ev.data.pose?.heading_deg.toFixed(0)}° → ${ev.data.next_cmd}`);
          }
        } else if (ev.event === "ack") {
          const a = ev.data as AckEventData;
          setLoopLog(prev => [...prev, {
            step: a.step_idx, cmd: a.cmd, reply: a.reply,
            elapsed_ms: a.elapsed_ms, ok: a.ok,
          }]);
        } else if (ev.event === "done") {
          setMessage(`Done in ${ev.data.steps} steps. Sequence: ${ev.data.sequence || "(none)"} — ${ev.data.message}`);
        } else if (ev.event === "aborted") {
          setMessage(`Aborted after ${ev.data.steps} steps. Sequence so far: ${ev.data.sequence || "(none)"}`);
        } else if (ev.event === "stuck") {
          setMessage(`Stuck after ${ev.data.steps} steps — robot stopped making progress. Check motors / BT link.`);
        } else if (ev.event === "step_budget_exceeded") {
          setMessage(`Step budget (${ev.data.max_steps}) exceeded — increase closed_loop.max_steps in settings.yaml if the path is genuinely long.`);
        } else if (ev.event === "error") {
          if (ev.data.frame_b64) setImageB64(ev.data.frame_b64);
          setMessage(`Error: ${ev.data.error}${ev.data.message ? " — " + ev.data.message : ""}`);
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") setMessage(`Stream failed: ${e}`);
    } finally {
      setStreaming(false);
      streamAbortRef.current = null;
    }
  };

  const handleAbort = async () => {
    if (!streaming) return;
    try {
      await abortExecute();
      setMessage("Abort signalled — waiting for current step to finish.");
    } catch (e) {
      setMessage(`Abort failed: ${e}`);
    }
  };

  const handleManual = async (cmd: "F" | "B" | "L" | "R" | "S") => {
    if (executing || streaming) return;
    setExecuting(true);
    setMessage(`Sending ${cmd}…`);
    try {
      const r = await sendRobotCommand(cmd);
      setMessage(r.ok ? `OK (${cmd})` : `Failed: ${r.error ?? "unknown error"}`);
    } catch (e) {
      setMessage(String(e));
    } finally {
      setExecuting(false);
    }
  };

  const busy = executing || streaming;

  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-3 space-y-3">
        <div className="flex items-center gap-2 p-2 rounded border border-white/10">
          <span className={`text-xs px-2 py-1 rounded ${simMode ? "bg-amber-700" : "bg-emerald-700"}`}>
            {simMode ? "🧪 SIM" : "🔌 LIVE BT"}
          </span>
          <button
            type="button"
            onClick={handleToggleSim}
            disabled={busy}
            className="text-xs underline text-white/70 hover:text-white disabled:opacity-40"
          >
            switch
          </button>
        </div>
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
        <div className="flex gap-2 flex-wrap items-center">
          <button type="button" onClick={handleCapture} className="px-3 py-1 bg-gray-600 rounded" title="Grab a raw frame from the camera">Capture</button>
          <button type="button" onClick={handleDetect} className="px-3 py-1 bg-blue-600 rounded" title="Find the robot's pose in the current frame">Detect</button>
          <button type="button" onClick={handleDetectShelves} className="px-3 py-1 bg-cyan-600 rounded" title="Find shelves in the current frame and save them">Detect shelves</button>
          <button type="button" onClick={handlePlan} className="px-3 py-1 bg-green-600 rounded" title="Plan a path between the selected shelves">Plan</button>
          <label className="flex items-center gap-1 text-sm text-white/70 ml-2" title="Auto-refresh the camera frame every 400 ms">
            <input
              type="checkbox"
              checked={livePreview}
              onChange={e => setLivePreview(e.target.checked)}
            />
            Live preview
          </label>
        </div>
        {imageB64 && (
          <img src={`data:image/png;base64,${imageB64}`} alt="vision feed" className="w-full border border-white/20" />
        )}
        {message && <div className="text-sm text-white/80">{message}</div>}

        {loopLog.length > 0 && (
          <div className="text-xs font-mono bg-black/50 border border-white/10 rounded p-2 max-h-40 overflow-auto">
            <div className="text-white/40 mb-1">Closed-loop command log</div>
            {loopLog.map((e, i) => (
              <div key={i} className={e.ok ? "text-white/80" : "text-red-400"}>
                [{String(e.step).padStart(2, " ")}] {e.cmd} → {e.reply} ({e.elapsed_ms} ms)
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="col-span-3 space-y-2">
        <div className="font-bold">Waypoints</div>
        <ol className="text-sm space-y-1 max-h-72 overflow-auto">
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

        <button
          type="button"
          onClick={handleExecuteClosedLoop}
          disabled={busy || !dst || (taskType === "pick_place" && !src)}
          className="w-full px-3 py-2 bg-purple-600 rounded disabled:bg-gray-700 disabled:opacity-50"
          title="Capture, replan, send one char, repeat. Frame updates after every step."
        >
          {streaming ? "Closed-loop running…" : "Execute (closed-loop)"}
        </button>
        {streaming && (
          <button
            type="button"
            onClick={handleAbort}
            className="w-full px-3 py-2 bg-red-700 rounded"
            title="Stop after the current step finishes"
          >
            Abort
          </button>
        )}

        <button
          type="button"
          onClick={handleExecute}
          disabled={busy || !dst || (taskType === "pick_place" && !src)}
          className="w-full px-3 py-2 bg-red-600 rounded disabled:bg-gray-700 disabled:opacity-50"
          title="Open-loop: plan once and blast the whole sequence. Useful for debugging."
        >
          {executing ? "Executing…" : "Execute (open-loop)"}
        </button>

        <div className="pt-3 mt-3 border-t border-white/10">
          <div className="text-xs text-white/50 mb-2">Manual control</div>
          <div className="grid grid-cols-3 gap-1 max-w-40 mx-auto">
            <div />
            <button
              type="button"
              onClick={() => handleManual("F")}
              disabled={busy}
              className="px-3 py-2 bg-blue-700 rounded disabled:opacity-40"
              title="Forward one cell"
            >▲</button>
            <div />
            <button
              type="button"
              onClick={() => handleManual("L")}
              disabled={busy}
              className="px-3 py-2 bg-blue-700 rounded disabled:opacity-40"
              title="Turn left 90°"
            >◀</button>
            <button
              type="button"
              onClick={() => handleManual("S")}
              disabled={busy}
              className="px-3 py-2 bg-gray-600 rounded disabled:opacity-40"
              title="Stop"
            >■</button>
            <button
              type="button"
              onClick={() => handleManual("R")}
              disabled={busy}
              className="px-3 py-2 bg-blue-700 rounded disabled:opacity-40"
              title="Turn right 90°"
            >▶</button>
            <div />
            <button
              type="button"
              onClick={() => handleManual("B")}
              disabled={busy}
              className="px-3 py-2 bg-blue-700 rounded disabled:opacity-40"
              title="Backward one cell"
            >▼</button>
            <div />
          </div>
        </div>
      </div>
    </div>
  );
}
