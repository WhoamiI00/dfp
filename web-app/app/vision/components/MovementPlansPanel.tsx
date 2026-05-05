"use client";
import { useCallback, useEffect, useState } from "react";
import {
  listPlans, savePlan, deletePlan, runPlan,
  type MovementPlan, type MovementStep, type MovementStepType,
  type MovementPlanRunResult,
} from "../lib/api";

// Step-type metadata: how to render & what params it needs.
type ParamKind = "duration" | "target_cm" | "none";

const STEP_META: Record<MovementStepType, { label: string; param: ParamKind; defaultMs?: number; defaultCm?: number }> = {
  drive_forward:  { label: "Drive forward",  param: "duration",  defaultMs: 1000 },
  drive_backward: { label: "Drive backward", param: "duration",  defaultMs: 1000 },
  turn_left:      { label: "Turn left",      param: "duration",  defaultMs: 800 },
  turn_right:     { label: "Turn right",     param: "duration",  defaultMs: 800 },
  lift_to:        { label: "Lift to (cm)",   param: "target_cm", defaultCm: 25 },
  lift_up_for:    { label: "Lift up (timed)",   param: "duration", defaultMs: 1500 },
  lift_down_for:  { label: "Lift down (timed)", param: "duration", defaultMs: 1500 },
  slider_extend:  { label: "Slider extend",  param: "none" },
  slider_retract: { label: "Slider retract", param: "none" },
  gripper_open:   { label: "Gripper open",   param: "none" },
  gripper_close:  { label: "Gripper close",  param: "none" },
  wait:           { label: "Wait",           param: "duration", defaultMs: 500 },
};

const STEP_TYPES = Object.keys(STEP_META) as MovementStepType[];

function makeStep(type: MovementStepType): MovementStep {
  const m = STEP_META[type];
  return {
    type,
    duration_ms: m.defaultMs ?? 0,
    target_cm: m.defaultCm ?? 0,
    note: "",
  };
}

function emptyPlan(name: string): MovementPlan {
  return { name, steps: [], note: "" };
}

export default function MovementPlansPanel() {
  const [plans, setPlans] = useState<MovementPlan[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState<MovementPlan | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastRun, setLastRun] = useState<MovementPlanRunResult | null>(null);
  const [addStepType, setAddStepType] = useState<MovementStepType>("drive_forward");

  const refresh = useCallback(async () => {
    try {
      const r = await listPlans();
      setPlans(r.plans);
    } catch (e) {
      setMessage(`Load plans failed: ${e}`);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Hydrate the draft from a saved plan when the user picks one from the
  // sidebar. We *only* depend on `selected` here — depending on `plans`
  // would re-fire after every refresh and clobber in-progress edits.
  // For the brand-new "+ New" path, handleNew sets the draft itself, so
  // the missing plan in `plans` is fine.
  useEffect(() => {
    if (selected === null) { setDraft(null); return; }
    // Use functional updates so we read the latest `plans` without depending
    // on it (which would retrigger this effect when plans refreshes).
    setPlans(currentPlans => {
      const found = currentPlans.find(p => p.name === selected);
      if (found) {
        setDraft({
          name: found.name,
          steps: found.steps.map(s => ({ ...s })),
          note: found.note,
        });
      }
      return currentPlans;
    });
  }, [selected]);

  const handleNew = () => {
    const name = prompt("New plan name:");
    if (!name) return;
    if (plans.some(p => p.name === name)) {
      setMessage(`A plan named "${name}" already exists.`);
      return;
    }
    setDraft(emptyPlan(name));
    setSelected(name);
  };

  const handleSave = async () => {
    if (!draft) return;
    if (!draft.name.trim()) {
      setMessage("Plan name can't be empty.");
      return;
    }
    setBusy(true);
    try {
      console.log("[plans] saving", draft);
      const saved = await savePlan(draft.name, draft);
      console.log("[plans] saved response:", saved);
      // Re-list to verify persistence — surfaces the case where the PUT
      // succeeded but the listing doesn't include it (would indicate a
      // backend bug rather than a network failure).
      const r = await listPlans();
      const present = r.plans.some(p => p.name === draft.name);
      setPlans(r.plans);
      if (!present) {
        setMessage(`⚠ Saved "${draft.name}" but it didn't appear in the list. Check the backend log.`);
      } else {
        setMessage(`✓ Saved "${draft.name}" (${draft.steps.length} steps).`);
      }
      setSelected(draft.name);
    } catch (e) {
      console.error("[plans] save failed", e);
      setMessage(`Save failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!draft) return;
    if (!confirm(`Delete plan "${draft.name}"?`)) return;
    setBusy(true);
    try {
      await deletePlan(draft.name);
      setMessage(`Deleted "${draft.name}".`);
      setDraft(null);
      setSelected(null);
      await refresh();
    } catch (e) {
      setMessage(`Delete failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const handleRun = async () => {
    if (!draft) return;
    setBusy(true);
    setLastRun(null);
    setMessage("Running plan…");
    try {
      const r = await runPlan(draft.name);
      setLastRun(r);
      setMessage(
        r.ok
          ? `Plan "${r.plan_name}" finished${r.sim ? " (sim)" : ""} in ${r.steps.length} step(s).`
          : `Plan "${r.plan_name}" failed at step ${r.steps.length}: ${r.error ?? "unknown error"}`,
      );
    } catch (e) {
      setMessage(`Run failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const updateStep = (idx: number, patch: Partial<MovementStep>) => {
    if (!draft) return;
    const next = draft.steps.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    setDraft({ ...draft, steps: next });
  };

  const moveStep = (idx: number, dir: -1 | 1) => {
    if (!draft) return;
    const j = idx + dir;
    if (j < 0 || j >= draft.steps.length) return;
    const next = [...draft.steps];
    [next[idx], next[j]] = [next[j], next[idx]];
    setDraft({ ...draft, steps: next });
  };

  const removeStep = (idx: number) => {
    if (!draft) return;
    setDraft({ ...draft, steps: draft.steps.filter((_, i) => i !== idx) });
  };

  const addStep = () => {
    if (!draft) return;
    setDraft({ ...draft, steps: [...draft.steps, makeStep(addStepType)] });
  };

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold">Movement plans</h3>
        <span className="text-xs text-white/50">
          Build and save scripted robot maneuvers. Run executes against the configured link (sim or wifi).
        </span>
      </div>

      <div className="grid grid-cols-12 gap-3">
        {/* Plans list (left) */}
        <div className="col-span-3 border border-white/10 rounded p-2 space-y-1 min-h-[280px]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-white/60">{plans.length} saved</span>
            <button
              type="button"
              onClick={handleNew}
              className="text-xs px-2 py-0.5 bg-blue-600 rounded"
            >
              + New
            </button>
          </div>
          {plans.length === 0 && (
            <div className="text-xs text-white/40 p-2">No plans yet.</div>
          )}
          {plans.map(p => (
            <button
              key={p.name}
              type="button"
              onClick={() => setSelected(p.name)}
              className={
                "w-full text-left px-2 py-1 text-sm rounded " +
                (selected === p.name ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/5")
              }
            >
              {p.name}
              <span className="text-xs text-white/40 ml-1">({p.steps.length})</span>
            </button>
          ))}
        </div>

        {/* Editor (right) */}
        <div className="col-span-9 border border-white/10 rounded p-3 space-y-3 min-h-[280px]">
          {!draft ? (
            <div className="text-sm text-white/50 text-center py-12">
              Select a plan on the left, or click <strong>+ New</strong> to start one.
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <input
                  value={draft.name}
                  onChange={e => setDraft({ ...draft, name: e.target.value })}
                  className="bg-black border border-white/20 px-2 py-1 text-sm font-bold flex-1"
                  placeholder="Plan name"
                />
                <button
                  type="button" onClick={handleSave} disabled={busy}
                  className="px-3 py-1.5 bg-green-600 rounded text-sm disabled:opacity-50"
                >Save</button>
                <button
                  type="button" onClick={handleRun}
                  disabled={busy || draft.steps.length === 0}
                  className="px-3 py-1.5 bg-blue-600 rounded text-sm disabled:opacity-50"
                >▶ Run</button>
                <button
                  type="button" onClick={handleDelete}
                  disabled={busy || !plans.some(p => p.name === draft.name)}
                  className="px-3 py-1.5 bg-red-600/70 rounded text-sm disabled:opacity-50"
                >Delete</button>
              </div>

              <input
                value={draft.note}
                onChange={e => setDraft({ ...draft, note: e.target.value })}
                placeholder="Optional note / description"
                className="w-full bg-black border border-white/10 px-2 py-1 text-xs"
              />

              {/* Steps */}
              <div className="space-y-1">
                {draft.steps.length === 0 && (
                  <div className="text-xs text-white/40 italic py-2">No steps yet.</div>
                )}
                {draft.steps.map((s, i) => {
                  const meta = STEP_META[s.type];
                  return (
                    <div key={i} className="flex items-center gap-2 bg-white/5 rounded p-1.5 text-sm">
                      <span className="text-xs text-white/40 w-6 text-right">{i + 1}.</span>
                      <select
                        aria-label={`Step ${i + 1} type`}
                        value={s.type}
                        onChange={e => {
                          const t = e.target.value as MovementStepType;
                          const m = STEP_META[t];
                          updateStep(i, {
                            type: t,
                            duration_ms: m.defaultMs ?? s.duration_ms,
                            target_cm: m.defaultCm ?? s.target_cm,
                          });
                        }}
                        className="bg-black border border-white/20 px-1 py-0.5 text-xs"
                      >
                        {STEP_TYPES.map(t => (
                          <option key={t} value={t}>{STEP_META[t].label}</option>
                        ))}
                      </select>

                      {meta.param === "duration" && (
                        <label className="text-xs flex items-center gap-1">
                          <input
                            type="number" min={1} max={60000} step={100}
                            value={s.duration_ms}
                            onChange={e => updateStep(i, { duration_ms: parseInt(e.target.value || "0") })}
                            className="bg-black border border-white/20 px-1 py-0.5 w-20"
                          />
                          <span className="text-white/50">ms</span>
                        </label>
                      )}
                      {meta.param === "target_cm" && (
                        <label className="text-xs flex items-center gap-1">
                          <input
                            type="number" min={1} max={50} step={0.5}
                            value={s.target_cm}
                            onChange={e => updateStep(i, { target_cm: parseFloat(e.target.value || "0") })}
                            className="bg-black border border-white/20 px-1 py-0.5 w-16"
                          />
                          <span className="text-white/50">cm</span>
                        </label>
                      )}

                      <input
                        value={s.note}
                        onChange={e => updateStep(i, { note: e.target.value })}
                        placeholder="note"
                        className="bg-black border border-white/10 px-1 py-0.5 text-xs flex-1 min-w-0"
                      />

                      <div className="flex items-center gap-0.5 ml-auto">
                        <button type="button" onClick={() => moveStep(i, -1)} disabled={i === 0}
                          className="px-1.5 text-white/60 hover:text-white disabled:opacity-30">↑</button>
                        <button type="button" onClick={() => moveStep(i, 1)} disabled={i === draft.steps.length - 1}
                          className="px-1.5 text-white/60 hover:text-white disabled:opacity-30">↓</button>
                        <button type="button" onClick={() => removeStep(i)}
                          className="px-1.5 text-red-400 hover:text-red-300">✕</button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Add step */}
              <div className="flex items-center gap-2 border-t border-white/10 pt-2">
                <select
                  aria-label="New step type"
                  value={addStepType}
                  onChange={e => setAddStepType(e.target.value as MovementStepType)}
                  className="bg-black border border-white/20 px-2 py-1 text-xs"
                >
                  {STEP_TYPES.map(t => <option key={t} value={t}>{STEP_META[t].label}</option>)}
                </select>
                <button
                  type="button" onClick={addStep}
                  className="px-2 py-1 bg-white/10 rounded text-xs hover:bg-white/20"
                >+ Add step</button>
              </div>

              {/* Run trace */}
              {lastRun && (
                <div className="border-t border-white/10 pt-2">
                  <div className="text-xs text-white/60 mb-1">
                    Last run: {lastRun.ok ? "✓ ok" : "✗ failed"}{lastRun.sim && " (sim)"} — {lastRun.steps.length} step(s)
                  </div>
                  <div className="max-h-40 overflow-auto bg-black/40 p-2 rounded text-xs space-y-0.5">
                    {lastRun.steps.map((s, i) => (
                      <div key={i} className={s.ok ? "text-green-300" : "text-red-300"}>
                        {s.ok ? "✓" : "✗"} {s.label} ({s.elapsed_ms}ms){s.error ? ` — ${s.error}` : ""}
                      </div>
                    ))}
                    {lastRun.error && !lastRun.ok && (
                      <div className="text-red-400 italic mt-1">{lastRun.error}</div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {message && (
        <div className="text-sm text-white/80 bg-white/5 border border-white/10 rounded p-2">
          {message}
        </div>
      )}
    </div>
  );
}
