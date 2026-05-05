"use client";
import { useEffect, useRef, useState } from "react";
import { getSettings, executeCanned, type CannedExecuteStep } from "../lib/api";

// Hold-to-move buttons: pointerdown sends start char, pointerup sends release.
// Heartbeat re-sends the start char every 150 ms while held so the ESP32's
// 300 ms watchdog never triggers. If the page hides or loses focus the
// watchdog stops the motor — same fault model as the ESP32's own page.

const HEARTBEAT_MS = 150;
const DIST_POLL_MS = 200;

type HoldCmd = "F" | "B" | "L" | "R" | "U" | "D" | "I" | "O";
type TapCmd = "S" | "u" | "i" | "G" | "N" | "H" | "X";

const RELEASE: Record<HoldCmd, TapCmd> = {
  F: "S", B: "S", L: "S", R: "S",
  U: "u", D: "u",
  I: "i", O: "i",
};

export default function ManualTab() {
  const [host, setHost] = useState<string>("");
  const [port, setPort] = useState<number>(80);
  const [linkType, setLinkType] = useState<string>("wifi");
  const [status, setStatus] = useState<string>("loading…");
  const [distance, setDistance] = useState<number | null>(null);
  const [reachable, setReachable] = useState<boolean>(false);

  // One useRef so all the hold buttons share the same heartbeat timer
  // bookkeeping — only one button can be held at a time per pointer, but
  // independent subsystems (drive + lift + slider) might overlap.
  const heartbeatsRef = useRef<Map<HoldCmd, number>>(new Map());

  // "Run Planned" state.
  const [planRunning, setPlanRunning] = useState(false);
  const [planSteps, setPlanSteps] = useState<CannedExecuteStep[]>([]);
  const [planError, setPlanError] = useState<string | null>(null);

  // Hardcoded source/dest for the demo move.
  // shelf_1_c (top, 5cm) -> shelf_2_a (bottom, 25cm).
  const PLANNED_FROM = "shelf_1_c";
  const PLANNED_TO = "shelf_2_a";

  const baseUrl = host ? `http://${host}:${port}` : "";

  // Pull ESP32 host from /api/settings on mount.
  useEffect(() => {
    (async () => {
      try {
        const s = await getSettings();
        if (s.robot_link) {
          setHost(s.robot_link.host);
          setPort(s.robot_link.port);
          setLinkType(s.robot_link.type);
          setStatus(
            s.robot_link.type === "sim"
              ? "robot_link.type is 'sim' — manual control is disabled."
              : `Linked to ${s.robot_link.host}:${s.robot_link.port}`,
          );
        } else {
          setStatus("Backend has no robot_link config. Check settings.yaml.");
        }
      } catch (e) {
        setStatus(`Failed to load settings: ${e}`);
      }
    })();
  }, []);

  // Distance polling. Runs every DIST_POLL_MS while host is set.
  useEffect(() => {
    if (!baseUrl || linkType === "sim") return;
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      try {
        const r = await fetch(`${baseUrl}/distance`, { cache: "no-store" });
        const t = (await r.text()).trim();
        const v = parseFloat(t);
        if (!cancelled) {
          if (isNaN(v) || v < 0) {
            setDistance(null);
          } else {
            setDistance(v);
          }
          setReachable(true);
        }
      } catch {
        if (!cancelled) {
          setReachable(false);
          setDistance(null);
        }
      }
    };
    tick();
    const id = setInterval(tick, DIST_POLL_MS);
    return () => { cancelled = true; clearInterval(id); };
  }, [baseUrl, linkType]);

  // Stop everything when the user navigates away or the page hides. The
  // ESP32 watchdog already does this on its own, but a proactive STOP ALL
  // is faster and shows up in serial logs as deliberate.
  useEffect(() => {
    if (!baseUrl) return;
    const panic = () => fetch(`${baseUrl}/cmd?val=X`, { cache: "no-store" }).catch(() => {});
    const onHide = () => { if (document.hidden) panic(); };
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", panic);
    return () => {
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", panic);
    };
  }, [baseUrl]);

  // Fire-and-forget — used by hold heartbeats where a missed tick is fine
  // (the next 150ms beat will catch up).
  const send = (val: string) => {
    if (!baseUrl) return Promise.resolve();
    return fetch(`${baseUrl}/cmd?val=${encodeURIComponent(val)}`, { cache: "no-store" })
      .then(() => { setReachable(true); })
      .catch(() => { setReachable(false); });
  };

  // Retry-until-ack — used by single-shot taps (gripper, slider stop) where
  // a dropped packet means the action never happens. The ESP32 confirms with
  // "OK" so we read the body and retry if we don't see it. Servo commands are
  // idempotent (sending G twice still leaves the gripper open) so retries
  // are safe. Returns true if the firmware acknowledged within `tries`.
  const sendReliable = async (val: string, tries = 4): Promise<boolean> => {
    if (!baseUrl) return false;
    for (let i = 0; i < tries; i++) {
      try {
        const r = await fetch(
          `${baseUrl}/cmd?val=${encodeURIComponent(val)}`,
          { cache: "no-store" },
        );
        if (r.ok) {
          const text = (await r.text()).trim();
          // ESP32 replies "OK" on success. Anything else (incl empty
          // body on flaky links) → retry.
          if (text === "OK" || text.startsWith("OK")) {
            setReachable(true);
            return true;
          }
        }
      } catch {
        setReachable(false);
      }
      // Backoff before retry. Keep it short — gripper feels unresponsive
      // beyond ~300ms total.
      await new Promise(res => setTimeout(res, 60 + i * 30));
    }
    setReachable(false);
    return false;
  };

  // Visual feedback for taps so the operator can tell the command landed.
  // Keys are tap chars, values are timestamps of last action.
  const [tapState, setTapState] = useState<Record<string, "sending" | "ok" | "fail">>({});

  const tap = async (val: string) => {
    setTapState(s => ({ ...s, [val]: "sending" }));
    const ok = await sendReliable(val);
    setTapState(s => ({ ...s, [val]: ok ? "ok" : "fail" }));
    // Clear the indicator after a short flash so repeated taps re-flash.
    window.setTimeout(() => {
      setTapState(s => {
        const next = { ...s };
        delete next[val];
        return next;
      });
    }, 600);
  };

  const startHold = (cmd: HoldCmd) => {
    if (heartbeatsRef.current.has(cmd)) return;
    send(cmd);
    const id = window.setInterval(() => send(cmd), HEARTBEAT_MS);
    heartbeatsRef.current.set(cmd, id);
  };

  const stopHold = (cmd: HoldCmd) => {
    const id = heartbeatsRef.current.get(cmd);
    if (id !== undefined) {
      window.clearInterval(id);
      heartbeatsRef.current.delete(cmd);
      send(RELEASE[cmd]);
    }
  };

  const stopAllHolds = () => {
    for (const [cmd, id] of heartbeatsRef.current.entries()) {
      window.clearInterval(id);
      heartbeatsRef.current.delete(cmd);
      send(RELEASE[cmd]);
    }
  };

  const runPlanned = async () => {
    if (planRunning) return;
    setPlanRunning(true);
    setPlanSteps([]);
    setPlanError(null);
    try {
      const r = await executeCanned({ from_shelf: PLANNED_FROM, to_shelf: PLANNED_TO });
      setPlanSteps(r.steps);
      if (!r.ok) setPlanError(r.error || "execution failed");
    } catch (e) {
      setPlanError(String(e));
    } finally {
      setPlanRunning(false);
    }
  };

  const disabled = linkType === "sim" || !host;

  // Distance color: <10cm red, <25cm amber, >=25cm green, null grey.
  const distColor = distance == null
    ? "text-white/40"
    : distance < 10
      ? "text-red-400"
      : distance < 25
        ? "text-amber-300"
        : "text-emerald-400";

  return (
    <div className="space-y-4 max-w-2xl">
      {/* Status bar */}
      <div className="flex items-center justify-between p-3 rounded border border-white/10 bg-white/5">
        <div className="text-sm">
          <div className="font-mono">{host || "—"}{host && `:${port}`}</div>
          <div className={`text-xs ${reachable ? "text-emerald-400" : "text-red-400"}`}>
            {linkType === "sim" ? "SIM mode" : (reachable ? "● connected" : "○ unreachable")}
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-white/50 tracking-widest">DISTANCE</div>
          <div className={`font-mono text-3xl font-bold ${distColor}`}>
            {distance == null ? "—" : distance.toFixed(1)}
            <span className="text-sm text-white/40 ml-1">cm</span>
          </div>
        </div>
      </div>

      {status && (
        <div className="text-xs text-white/50">{status}</div>
      )}

      {/* STOP ALL */}
      <button
        type="button"
        onClick={() => { stopAllHolds(); send("X"); }}
        disabled={disabled}
        className="w-full py-4 rounded-xl bg-red-700 hover:bg-red-600 disabled:bg-gray-800 disabled:opacity-50 text-white text-2xl font-bold tracking-widest active:translate-y-0.5"
      >
        STOP ALL
      </button>

      {/* RUN PLANNED — hardcoded shelf_1_c -> shelf_2_b dead-reckoning move */}
      <div className="p-3 border border-purple-500/40 bg-purple-500/5 rounded-xl space-y-2">
        <div className="text-xs text-purple-300/80 tracking-widest text-center">
          RUN PLANNED ({PLANNED_FROM} → {PLANNED_TO})
        </div>
        <button
          type="button"
          onClick={runPlanned}
          disabled={disabled || planRunning}
          className="w-full py-3 rounded-lg bg-purple-700 hover:bg-purple-600 disabled:bg-gray-800 disabled:opacity-50 text-white font-bold tracking-wide active:translate-y-0.5"
        >
          {planRunning ? "Running…" : "Run Planned"}
        </button>
        {(planSteps.length > 0 || planError) && (
          <div className="font-mono text-xs bg-black/40 border border-white/10 rounded p-2 max-h-44 overflow-auto">
            {planSteps.map((s, i) => (
              <div key={i} className={s.ok ? "text-white/80" : "text-red-400"}>
                [{String(i).padStart(2, " ")}] {s.label} → {s.reply || "OK"} ({s.elapsed_ms}ms)
                {s.error && <span className="text-red-300"> — {s.error}</span>}
              </div>
            ))}
            {planError && <div className="text-red-400 mt-1">✗ {planError}</div>}
          </div>
        )}
      </div>

      {/* DRIVE */}
      <Group title="DRIVE (hold)">
        <Row>
          <HoldButton cmd="F" label="FWD" onStart={startHold} onStop={stopHold} disabled={disabled} />
        </Row>
        <Row>
          <HoldButton cmd="L" label="LEFT" onStart={startHold} onStop={stopHold} disabled={disabled} />
          <TapButton onClick={() => send("S")} label="STOP" stop disabled={disabled} />
          <HoldButton cmd="R" label="RIGHT" onStart={startHold} onStop={stopHold} disabled={disabled} />
        </Row>
        <Row>
          <HoldButton cmd="B" label="BACK" onStart={startHold} onStop={stopHold} disabled={disabled} />
        </Row>
      </Group>

      {/* LIFT */}
      <Group title="LIFT (hold)">
        <Row>
          <HoldButton cmd="U" label="UP" onStart={startHold} onStop={stopHold} disabled={disabled} />
          <TapButton onClick={() => send("u")} label="STOP" stop disabled={disabled} />
          <HoldButton cmd="D" label="DOWN" onStart={startHold} onStop={stopHold} disabled={disabled} />
        </Row>
      </Group>

      {/* SLIDER */}
      <Group title="SLIDER (hold)">
        <Row>
          <HoldButton cmd="I" label="IN" onStart={startHold} onStop={stopHold} disabled={disabled} />
          <TapButton onClick={() => send("i")} label="STOP" stop disabled={disabled} />
          <HoldButton cmd="O" label="OUT" onStart={startHold} onStop={stopHold} disabled={disabled} />
        </Row>
      </Group>

      {/* GRIPPER — uses retry-until-ack so a dropped packet on flaky WiFi
          doesn't silently miss the command. Each tap retries up to 4 times
          before giving up; the button briefly flashes its result. */}
      <Group title="GRIPPER (reliable tap)">
        <Row>
          <TapButton onClick={() => tap("G")} label="OPEN" go disabled={disabled} state={tapState.G} />
          <TapButton onClick={() => tap("H")} label="RELEASE" stop disabled={disabled} state={tapState.H} />
          <TapButton onClick={() => tap("N")} label="CLOSE" go disabled={disabled} state={tapState.N} />
        </Row>
      </Group>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="p-3 border border-white/10 rounded-xl">
      <div className="text-xs text-white/50 tracking-widest text-center mb-2">{title}</div>
      <div className="flex flex-col items-center gap-2">{children}</div>
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="flex gap-2 justify-center">{children}</div>;
}

function HoldButton({
  cmd, label, onStart, onStop, disabled,
}: {
  cmd: HoldCmd;
  label: string;
  onStart: (c: HoldCmd) => void;
  onStop: (c: HoldCmd) => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onPointerDown={(e) => { e.preventDefault(); onStart(cmd); }}
      onPointerUp={() => onStop(cmd)}
      onPointerLeave={() => onStop(cmd)}
      onPointerCancel={() => onStop(cmd)}
      className="w-24 h-24 rounded-xl bg-blue-800 hover:bg-blue-700 active:bg-blue-500 active:translate-y-0.5 disabled:bg-gray-800 disabled:opacity-50 text-white font-semibold select-none touch-none"
    >
      {label}
    </button>
  );
}

function TapButton({
  onClick, label, go = false, stop = false, disabled, state,
}: {
  onClick: () => void;
  label: string;
  go?: boolean;
  stop?: boolean;
  disabled: boolean;
  /** Visual feedback: "sending" (in-flight), "ok" (firmware acked),
   * "fail" (gave up after retries). Auto-clears after ~600ms. */
  state?: "sending" | "ok" | "fail";
}) {
  // State color overrides the base — sending=amber, ok=green, fail=red.
  const stateColor =
    state === "sending" ? "bg-amber-600 hover:bg-amber-600 ring-2 ring-amber-300" :
    state === "ok" ? "bg-emerald-500 hover:bg-emerald-500 ring-2 ring-emerald-200" :
    state === "fail" ? "bg-red-600 hover:bg-red-600 ring-2 ring-red-300" :
    null;
  const baseColor = stop
    ? "bg-red-800 hover:bg-red-700 active:bg-red-600"
    : go
      ? "bg-emerald-800 hover:bg-emerald-700 active:bg-emerald-600"
      : "bg-gray-700 hover:bg-gray-600";
  const color = stateColor ?? baseColor;
  const indicator =
    state === "sending" ? "…" :
    state === "ok" ? "✓" :
    state === "fail" ? "✕" :
    null;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`w-24 h-24 rounded-xl ${color} disabled:bg-gray-800 disabled:opacity-50 text-white font-semibold active:translate-y-0.5 transition-colors`}
    >
      <div>{label}</div>
      {indicator && <div className="text-xs mt-1 opacity-80">{indicator}</div>}
    </button>
  );
}
