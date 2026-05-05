"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getInventory, listOrders, createOrder, cancelOrder,
  previewReplenish, runReplenish,
  updateShelfInventory, runNextOrder,
  rlStatus, rlPredict,
  type ShelfInventory, type SkuTotal, type Order, type ReplenishProposal,
  type RunNextOrderResult, type RLPrediction, type RLStatus,
} from "../lib/api";
import { getShelves } from "../lib/api";
import type { Shelf } from "../lib/types";

const REFRESH_MS = 2000;
const DEFAULT_SKU = "widget";

// Layout: two racks (shelf_1, shelf_2) with floors a/b/c, plus conveyer.
// Top row = top floor (c). Conveyer rendered separately.
const RACK_IDS = ["shelf_1", "shelf_2"] as const;
const FLOORS = ["c", "b", "a"] as const;  // render top → bottom
const CONVEYER_ID = "conveyer";

export default function InventoryTab() {
  const [shelves, setShelves] = useState<Shelf[]>([]);
  const [shelfInv, setShelfInv] = useState<ShelfInventory[]>([]);
  const [skus, setSkus] = useState<SkuTotal[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [proposals, setProposals] = useState<ReplenishProposal[] | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [lastRun, setLastRun] = useState<RunNextOrderResult | null>(null);
  const [rl, setRl] = useState<{ status: RLStatus | null; pred: RLPrediction | null }>({
    status: null, pred: null,
  });

  // Manual order form
  const [newSku, setNewSku] = useState(DEFAULT_SKU);
  const [newSrc, setNewSrc] = useState("");
  const [newDst, setNewDst] = useState("");
  const [newQty, setNewQty] = useState(1);
  const [thresholdPct, setThresholdPct] = useState(30);

  const refresh = useCallback(async () => {
    try {
      const [inv, ord, sh] = await Promise.all([
        getInventory(),
        listOrders(),
        getShelves(),
      ]);
      setShelfInv(inv.shelves);
      setSkus(inv.skus);
      setOrders(ord.orders);
      setShelves(sh.shelves);
      if (sh.shelves.length >= 1 && !newSrc) setNewSrc(sh.shelves[0].id);
      if (sh.shelves.length >= 2 && !newDst) setNewDst(sh.shelves[1].id);
    } catch (e) {
      setMessage(`Refresh failed: ${e}`);
    }
  }, [newSrc, newDst]);

  // Light RL status poll — separate so its failure (service down) doesn't
  // break inventory refresh.
  const refreshRL = useCallback(async () => {
    try {
      const s = await rlStatus();
      setRl(prev => ({ ...prev, status: s }));
    } catch {
      setRl(prev => ({ ...prev, status: null }));
    }
  }, []);

  useEffect(() => {
    refresh();
    refreshRL();
    const id = setInterval(() => { refresh(); refreshRL(); }, REFRESH_MS);
    return () => clearInterval(id);
  }, [refresh, refreshRL]);

  const invByShelf = useMemo(() => {
    const m = new Map<string, ShelfInventory>();
    for (const s of shelfInv) m.set(s.shelf_id, s);
    return m;
  }, [shelfInv]);

  // Auto-refill activity log. Each entry is one RL-recommended order
  // queued in response to a rack slot losing stock. Entries persist until
  // the operator dismisses them (no auto-clear).
  type RefillAlert = {
    shelfId: string;
    orderId: number;
    sku: string;
    qty: number;
    rlReasoning: string;
    rlForecast: string;
    invBefore: number;
    invAfter: number;
    capacity: number;
    at: number;
  };
  const [refillAlerts, setRefillAlerts] = useState<RefillAlert[]>([]);
  // Shelf ids that just dropped — used to flash the slot UI for ~1.5s.
  const [recentlyChanged, setRecentlyChanged] = useState<Set<string>>(new Set());

  const dismissAlert = (orderId: number) => {
    setRefillAlerts(a => a.filter(x => x.orderId !== orderId));
  };
  const dismissAllAlerts = () => setRefillAlerts([]);

  const flashShelf = (shelfId: string) => {
    setRecentlyChanged(s => new Set(s).add(shelfId));
    window.setTimeout(() => {
      setRecentlyChanged(s => {
        const n = new Set(s);
        n.delete(shelfId);
        return n;
      });
    }, 1500);
  };

  // Universal stepper for any shelf (rack slots + conveyer). Adjusts the
  // count by `delta`. When the change is a *drop* on a rack slot (not the
  // conveyer), we treat it as "stock was consumed" and ask the RL model
  // how much to reorder, then queue that order from conveyer → slot.
  //
  // The RL model returns an order quantity 0–50 trained on day-of-week
  // demand. We scale that recommendation to fit the rack-slot capacity:
  // qty = clamp(round(rl.qty / 5), 1, free_space). That way a "model says
  // order 30" recommendation lands as ~6 units, which is plausible for
  // a 5-cap shelf, while preserving the relative magnitude of the model's
  // signal (low rec = low order, high rec = max-out).
  const handleStep = async (shelfId: string, delta: number) => {
    const cur = invByShelf.get(shelfId);
    if (!cur) return;
    const before = cur.inventory_count;
    const next = Math.max(0, Math.min(cur.capacity, before + delta));
    if (next === before) return;
    try {
      await updateShelfInventory(shelfId, {
        sku_id: cur.sku_id ?? DEFAULT_SKU,
        inventory_count: next,
      });
    } catch (e) {
      setMessage(`Step failed: ${e}`);
      return;
    }

    // Stock dropped on a rack slot → ask the RL model + queue an order.
    if (delta < 0 && shelfId !== CONVEYER_ID) {
      flashShelf(shelfId);
      const conveyer = invByShelf.get(CONVEYER_ID);
      const sku = cur.sku_id ?? conveyer?.sku_id ?? DEFAULT_SKU;

      // Total widget inventory after the drop, used as RL model input.
      const widgetTotal = (skus.find(s => s.sku_id === sku)?.total ?? 0) + delta;
      const now = new Date();
      const dow = (now.getDay() + 6) % 7;  // JS Sun=0..Sat=6 -> Python Mon=0..Sun=6

      let rlQty = 1;
      let rlReasoning = "Heuristic fallback — RL service unreachable.";
      let rlForecast = "";
      try {
        const p = await rlPredict({
          inventory: Math.max(0, widgetTotal),
          day_index: now.getDate() % 30,
          day_of_week: dow,
        });
        // Map the model's 0-50 unit recommendation onto our 5-cap rack
        // slots: divide by 5, round, then clamp to [1, free space in slot].
        const free = cur.capacity - next;
        rlQty = Math.max(1, Math.min(free, Math.round(p.order_quantity / 5)));
        rlReasoning = p.reasoning;
        rlForecast = p.demand_forecast;
      } catch (e) {
        // RL offline — fall back to "refill to capacity" so the demo
        // still works without the service running.
        rlQty = Math.max(1, cur.capacity - next);
        rlReasoning = `RL service offline (${e}). Falling back: refill to capacity.`;
      }

      try {
        const o = await createOrder({
          sku_id: sku,
          source_shelf_id: CONVEYER_ID,
          destination_shelf_id: shelfId,
          qty: rlQty,
          reason: `RL forecast: ${rlReasoning.slice(0, 80)}`,
        });
        setRefillAlerts(a => [
          ...a,
          {
            shelfId, orderId: o.id, sku,
            qty: rlQty,
            rlReasoning, rlForecast,
            invBefore: before, invAfter: next, capacity: cur.capacity,
            at: Date.now(),
          },
        ]);
      } catch (e) {
        setMessage(`Auto-refill order failed for ${shelfId}: ${e}`);
      }
    }

    refresh();
  };

  const handleCreate = async () => {
    if (!newSrc || !newDst || newSrc === newDst) {
      setMessage("Pick two different shelves.");
      return;
    }
    try {
      const o = await createOrder({
        sku_id: newSku, source_shelf_id: newSrc,
        destination_shelf_id: newDst, qty: newQty,
        reason: "manual",
      });
      setMessage(`Order #${o.id} queued.`);
      refresh();
    } catch (e) {
      setMessage(`Create failed: ${e}`);
    }
  };

  const handleCancel = async (id: number) => {
    try {
      await cancelOrder(id);
      setMessage(`Order #${id} cancelled.`);
      refresh();
    } catch (e) {
      setMessage(`Cancel failed: ${e}`);
    }
  };

  const handleRunNext = async () => {
    setBusy(true);
    setMessage("Running next order…");
    try {
      const r = await runNextOrder();
      setLastRun(r);
      setMessage(r.message);
      refresh();
    } catch (e) {
      setMessage(`Run failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const handlePreview = async () => {
    try {
      const r = await previewReplenish(thresholdPct / 100);
      setProposals(r.proposals);
      setMessage(
        r.proposals.length === 0
          ? "Brain says: nothing to refill."
          : `Brain proposes ${r.proposals.length} refill order(s).`,
      );
    } catch (e) {
      setMessage(`Preview failed: ${e}`);
    }
  };

  const handleRunReplenish = async () => {
    try {
      const r = await runReplenish(thresholdPct / 100);
      setProposals(null);
      setMessage(`Enqueued ${r.enqueued.length} order(s)` +
        (r.skipped.length ? `, skipped ${r.skipped.length} duplicate(s).` : "."));
      refresh();
    } catch (e) {
      setMessage(`Run failed: ${e}`);
    }
  };

  // RL advisor: feed total widget inventory as the "warehouse stock", use
  // today's day-of-week. The RL model was trained on a single-product
  // demand simulator (0-100 inventory range), so we expose its raw
  // recommendation as guidance, not as an executed action.
  const handleAskRL = async () => {
    const widget = skus.find(s => s.sku_id === DEFAULT_SKU);
    const totalInv = widget?.total ?? 0;
    const now = new Date();
    const dow = (now.getDay() + 6) % 7;  // JS: 0=Sun..6=Sat -> Python: 0=Mon..6=Sun
    try {
      const p = await rlPredict({
        inventory: totalInv,
        day_index: now.getDate() % 30,
        day_of_week: dow,
      });
      setRl(prev => ({ ...prev, pred: p }));
      setMessage(`RL advisor: order ${p.order_quantity} unit(s).`);
    } catch (e) {
      setMessage(`RL advisor unreachable. Is inventory-rl running on :8000? (${e})`);
    }
  };

  const pendingCount = orders.filter(o => o.status === "pending").length;

  return (
    <div className="space-y-6">
      {/* === Top row: shelf grid visualization === */}
      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h3 className="text-lg font-bold">Warehouse layout</h3>
          <div className="text-xs text-white/60">
            Use the +/− steppers on each rack slot to simulate sales / restocks. When stock drops, the <span className="text-purple-300 font-semibold">🧠 RL model</span> picks the refill quantity and a conveyer→shelf order is queued automatically.
          </div>
        </div>
        <div className="flex flex-wrap items-stretch gap-8 p-4 bg-white/5 rounded border border-white/10">
          {/* Conveyer (left) — count is adjusted only via +/− steppers. */}
          <div className="flex items-end">
            <ConveyerCard
              inv={invByShelf.get(CONVEYER_ID)}
              onStep={(d) => handleStep(CONVEYER_ID, d)}
            />
          </div>
          {/* Arrow hint */}
          <div className="text-3xl text-white/30 self-center">→</div>
          {/* Two racks */}
          <div className="flex items-end gap-8">
            {RACK_IDS.map(rackId => (
              <RackCard
                key={rackId}
                rackId={rackId}
                floors={FLOORS}
                invByShelf={invByShelf}
                onStep={handleStep}
                recentlyChanged={recentlyChanged}
              />
            ))}
          </div>

          {/* Auto-refill notification panel (right side). When a rack
              slot is emptied, an order is queued and a transient card
              appears here. Cards fade out after 6 seconds. */}
          <div className="flex-1 min-w-[260px] flex flex-col gap-2 self-stretch">
            <div className="flex items-baseline justify-between">
              <div className="text-xs text-white/50 uppercase tracking-widest">
                auto-refill activity
              </div>
              {refillAlerts.length > 0 && (
                <button
                  type="button" onClick={dismissAllAlerts}
                  className="text-[10px] text-white/40 hover:text-white/70 underline"
                >
                  clear all ({refillAlerts.length})
                </button>
              )}
            </div>
            {refillAlerts.length === 0 ? (
              <div className="text-xs text-white/40 italic border border-dashed border-white/10 rounded p-3 flex-1 flex items-center justify-center text-center">
                Empty a rack slot to trigger an auto-refill order from the conveyer.
              </div>
            ) : (
              <div className="space-y-2 flex-1 max-h-[260px] overflow-auto">
                {refillAlerts.slice().reverse().map(a => {
                  const critical = a.invAfter === 0;
                  const headline = critical
                    ? `${a.shelfId} is now EMPTY`
                    : `${a.shelfId} dropped to ${a.invAfter}/${a.capacity}`;
                  const accent = critical
                    ? "border-red-400/70 bg-red-500/10 ring-1 ring-red-400/30"
                    : "border-amber-400/60 bg-amber-500/10";
                  return (
                    <div key={`${a.shelfId}-${a.orderId}`}
                      className={`border ${accent} rounded-md p-2 relative shadow-md shadow-black/40 backdrop-blur-sm transition-all`}>
                      <button
                        type="button"
                        onClick={() => dismissAlert(a.orderId)}
                        title="Dismiss"
                        className="absolute top-1 right-1 text-white/40 hover:text-white text-xs leading-none px-1"
                      >
                        ✕
                      </button>
                      <div className={`text-sm font-bold flex items-center gap-2 pr-5 ${critical ? "text-red-300" : "text-amber-300"}`}>
                        <span>{critical ? "🚨" : "⚠"}</span>
                        <span>{headline}</span>
                      </div>
                      <div className="text-xs text-white/80 mt-1.5 flex items-baseline gap-2 flex-wrap">
                        <span className="px-1.5 py-0.5 rounded bg-purple-600/40 text-purple-100 font-bold text-[10px] uppercase tracking-wide">
                          🧠 RL
                        </span>
                        <span>
                          ordered <span className="font-bold text-green-300">{a.qty}</span> unit{a.qty === 1 ? "" : "s"}{" "}
                          <span className="text-white/50">(order #{a.orderId})</span>
                        </span>
                      </div>
                      <div className="text-[11px] text-white/60 mt-1 italic">
                        {a.rlReasoning}
                      </div>
                      {a.rlForecast && (
                        <div className="text-[10px] text-purple-200/70 mt-0.5">
                          📊 {a.rlForecast}
                        </div>
                      )}
                      <div className="text-[10px] text-white/40 mt-1 font-mono">
                        conveyer → {a.shelfId} · {a.invBefore}→{a.invAfter}/{a.capacity}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* === Middle row: dispatcher + per-SKU totals + RL advisor === */}
      <section className="grid grid-cols-12 gap-4">
        {/* Dispatcher */}
        <div className="col-span-4 border border-white/10 rounded p-3 space-y-2">
          <h3 className="font-bold">Dispatcher</h3>
          <div className="text-sm text-white/70">
            <div>Pending orders: <span className="font-bold text-amber-400">{pendingCount}</span></div>
          </div>
          <button
            type="button" onClick={handleRunNext}
            disabled={busy || pendingCount === 0}
            className="w-full px-3 py-2 bg-blue-600 rounded disabled:bg-white/10 disabled:text-white/40"
          >
            {busy ? "Running…" : "▶ Run next order (canned)"}
          </button>
          <div className="text-xs text-white/50">
            Pops the oldest pending order, drives the robot via canned pick-place,
            updates inventory on success.
          </div>
          {lastRun?.executed && (
            <details className="text-xs">
              <summary className="cursor-pointer text-white/70">Last run trace ({lastRun.executed.steps.length} steps)</summary>
              <div className="mt-1 max-h-40 overflow-auto bg-black/40 p-2 rounded">
                {lastRun.executed.steps.map((s, i) => (
                  <div key={i} className={s.ok ? "text-green-300" : "text-red-300"}>
                    {s.ok ? "✓" : "✗"} {s.label} ({s.elapsed_ms}ms){s.error ? ` — ${s.error}` : ""}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>

        {/* Stock per SKU */}
        <div className="col-span-4 border border-white/10 rounded p-3">
          <h3 className="font-bold mb-2">Stock per SKU</h3>
          {skus.length === 0 ? (
            <div className="text-sm text-white/50">No tracked SKUs. Toggle a slot above.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-white/60 border-b border-white/10">
                <tr><th className="text-left">SKU</th><th className="text-right">Total</th><th className="text-left pl-2">Locations</th></tr>
              </thead>
              <tbody>
                {skus.map(k => (
                  <tr key={k.sku_id} className="border-b border-white/5">
                    <td className="py-1">{k.sku_id}</td>
                    <td className="text-right">{k.total}/{k.capacity}</td>
                    <td className="pl-2 text-white/60 text-xs">{k.shelves.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* RL Advisor card */}
        <div className="col-span-4 border border-purple-500/40 rounded p-3 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-bold">🧠 RL Forecasting</h3>
            <span className={`text-xs ${rl.status?.model_loaded ? "text-green-400" : "text-amber-400"}`}>
              {rl.status ? (rl.status.model_loaded ? "model loaded" : "heuristic fallback") : "offline"}
            </span>
          </div>
          <button
            type="button" onClick={handleAskRL}
            className="w-full px-3 py-1.5 bg-purple-600 rounded text-sm"
          >
            Ask the model
          </button>
          {rl.pred && (
            <div className="text-xs space-y-1 bg-black/40 p-2 rounded">
              <div><span className="text-white/50">Order qty:</span> <span className="text-purple-300 font-bold">{rl.pred.order_quantity}</span></div>
              <div><span className="text-white/50">Status:</span> {rl.pred.inventory_status}</div>
              <div><span className="text-white/50">Forecast:</span> {rl.pred.demand_forecast}</div>
              <div className="pt-1 italic text-white/70">{rl.pred.reasoning}</div>
            </div>
          )}
          <div className="text-xs text-white/40">
            Single-product DQN/PPO trained on day-of-week demand. See the RL Forecasting tab for full controls.
          </div>
        </div>
      </section>

      {/* === Bottom row: manual order, auto-replenish, queue === */}
      <section className="grid grid-cols-12 gap-4">
        {/* Manual order */}
        <div className="col-span-4 border border-white/10 rounded p-3 space-y-2">
          <h3 className="font-bold">New order (manual)</h3>
          <label className="block text-sm">
            <span className="text-white/60">SKU</span>
            <input value={newSku} onChange={e => setNewSku(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1" />
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Source</span>
            <select value={newSrc} onChange={e => setNewSrc(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
              {shelves.map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Destination</span>
            <select value={newDst} onChange={e => setNewDst(e.target.value)} className="w-full bg-black border border-white/20 px-2 py-1">
              {shelves.filter(s => s.id !== newSrc).map(s => <option key={s.id} value={s.id}>{s.id}</option>)}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-white/60">Qty</span>
            <input type="number" min={1} value={newQty} onChange={e => setNewQty(parseInt(e.target.value || "1"))} className="w-full bg-black border border-white/20 px-2 py-1" />
          </label>
          <button type="button" onClick={handleCreate} className="w-full px-3 py-2 bg-blue-600 rounded">Queue order</button>
        </div>

        {/* Auto-replenish */}
        <div className="col-span-4 border border-white/10 rounded p-3 space-y-2">
          <h3 className="font-bold">Auto-replenish (rule-based)</h3>
          <label className="block text-sm">
            <span className="text-white/60">Low-stock threshold: {thresholdPct}%</span>
            <input type="range" min={5} max={95} value={thresholdPct} onChange={e => setThresholdPct(parseInt(e.target.value))} className="w-full" />
          </label>
          <div className="flex gap-2">
            <button type="button" onClick={handlePreview} className="flex-1 px-3 py-2 bg-amber-600 rounded">Preview</button>
            <button type="button" onClick={handleRunReplenish} className="flex-1 px-3 py-2 bg-green-600 rounded">Enqueue</button>
          </div>
          {proposals && proposals.length > 0 && (
            <div className="text-xs space-y-1 pt-2 border-t border-white/10">
              {proposals.map((p, i) => (
                <div key={i} className="text-white/70">
                  {p.qty}× <strong>{p.sku_id}</strong>: {p.source_shelf_id} → {p.destination_shelf_id}
                </div>
              ))}
            </div>
          )}
          <div className="text-xs text-white/40">
            Flags shelves below threshold and proposes refills from the fullest matching source.
          </div>
        </div>

        {/* Order queue */}
        <div className="col-span-4 space-y-2">
          <h3 className="font-bold">Order queue</h3>
          <div className="text-xs text-white/50">Newest first. Auto-refresh every 2s.</div>
          <div className="max-h-[400px] overflow-auto border border-white/10 rounded">
            {orders.length === 0 ? (
              <div className="p-3 text-sm text-white/50">No orders yet.</div>
            ) : (
              <table className="w-full text-xs">
                <thead className="text-white/60 sticky top-0 bg-black border-b border-white/10">
                  <tr>
                    <th className="text-left p-1">#</th>
                    <th className="text-left">SKU</th>
                    <th className="text-left">Route</th>
                    <th className="text-right">Qty</th>
                    <th className="text-left">Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(o => (
                    <tr key={o.id} className="border-b border-white/5">
                      <td className="p-1">{o.id}</td>
                      <td>{o.sku_id}</td>
                      <td className="text-white/70">{o.source_shelf_id}→{o.destination_shelf_id}</td>
                      <td className="text-right">{o.qty}</td>
                      <td>
                        <span className={
                          o.status === "pending" ? "text-amber-400" :
                          o.status === "running" ? "text-blue-400" :
                          o.status === "done" ? "text-green-400" :
                          o.status === "failed" ? "text-red-400" :
                          "text-white/50"
                        }>{o.status}</span>
                      </td>
                      <td>
                        {o.status === "pending" && (
                          <button type="button" onClick={() => handleCancel(o.id)} className="text-red-400 hover:text-red-300 text-xs">cancel</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </section>

      {message && (
        <div className="text-sm text-white/80 bg-white/5 border border-white/10 rounded p-2">
          {message}
        </div>
      )}
    </div>
  );
}

// --- Sub-components --------------------------------------------------------

function RackCard({
  rackId, floors, invByShelf, onStep, recentlyChanged,
}: {
  rackId: string;
  floors: readonly string[];
  invByShelf: Map<string, ShelfInventory>;
  onStep: (shelfId: string, delta: number) => void;
  /** Set of shelf ids that just had inventory drop — used to flash the slot. */
  recentlyChanged: Set<string>;
}) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="text-xs text-white/60 mb-1 font-mono tracking-widest">{rackId}</div>
      <div className="flex flex-col gap-1 border-2 border-white/30 rounded-md p-1.5 bg-gradient-to-b from-white/5 to-transparent">
        {floors.map(f => {
          const id = `${rackId}_${f}`;
          const inv = invByShelf.get(id);
          const count = inv?.inventory_count ?? 0;
          const cap = inv?.capacity ?? 5;
          const pct = cap > 0 ? count / cap : 0;
          const filled = count > 0;
          const flashing = recentlyChanged.has(id);

          // Color tier by fill %: red (empty/critical) -> amber (low) -> green (healthy).
          const tier =
            count === 0 ? "empty" :
            pct < 0.4 ? "low" :
            "healthy";
          const tierClasses = {
            empty: "from-red-900/40 to-red-700/20 border-red-500/40",
            low: "from-amber-900/40 to-amber-600/20 border-amber-400/60",
            healthy: "from-emerald-900/40 to-emerald-600/30 border-emerald-400",
          }[tier];
          const tierText = {
            empty: "text-red-300",
            low: "text-amber-300",
            healthy: "text-emerald-300",
          }[tier];
          const flashClass = flashing
            ? "ring-4 ring-red-400/60 ring-offset-2 ring-offset-black"
            : "";

          return (
            <div
              key={id}
              className={
                `relative w-28 h-20 rounded-md border-2 flex flex-col items-center justify-center ` +
                `transition-all duration-300 bg-gradient-to-br ${tierClasses} ${flashClass}`
              }
            >
              {/* Fill-level "liquid" indicator behind the content */}
              <div
                className={`absolute bottom-0 left-0 right-0 rounded-b-md transition-all duration-500 ${
                  tier === "empty" ? "bg-red-500/0" :
                  tier === "low" ? "bg-amber-500/30" :
                  "bg-emerald-500/30"
                }`}
                style={{ height: `${Math.max(8, pct * 100)}%` }}
              />
              {/* Content */}
              <div className="relative z-10 flex flex-col items-center">
                <div className={`text-xl ${filled ? "" : "opacity-30"}`}>📦</div>
                <div className={`text-sm font-bold ${tierText}`}>
                  {count}/{cap}
                </div>
                <div className="text-[9px] text-white/50">floor {f}</div>
              </div>
              {/* Steppers on the side */}
              <div className="absolute right-0 top-0 bottom-0 flex flex-col justify-around z-20">
                <button
                  type="button"
                  onClick={() => onStep(id, +1)}
                  disabled={count >= cap}
                  title="Add 1"
                  className="w-5 h-7 text-[10px] bg-white/10 hover:bg-emerald-600/50 disabled:opacity-20 rounded-l text-white"
                >+</button>
                <button
                  type="button"
                  onClick={() => onStep(id, -1)}
                  disabled={count <= 0}
                  title="Remove 1 (simulate sale)"
                  className="w-5 h-7 text-[10px] bg-white/10 hover:bg-red-600/50 disabled:opacity-20 rounded-l text-white"
                >−</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ConveyerCard({
  inv, onStep,
}: {
  inv: ShelfInventory | undefined;
  onStep: (delta: number) => void;
}) {
  const count = inv?.inventory_count ?? 0;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="text-xs text-white/60 mb-1">conveyer (inbound)</div>
      <div className="border-2 border-amber-400/60 rounded p-2 bg-amber-900/10 flex flex-col items-center gap-2 w-32">
        <div className="text-3xl" title={count > 0 ? "incoming stock" : "empty"}>
          {count > 0 ? "🚚" : "⏹"}
        </div>
        <div className="text-sm text-amber-300 font-bold">{count} unit{count === 1 ? "" : "s"}</div>
        <div className="flex gap-2">
          <button type="button" onClick={() => onStep(-1)} className="px-3 py-0.5 text-sm bg-white/10 rounded hover:bg-white/20">−</button>
          <button type="button" onClick={() => onStep(+1)} className="px-3 py-0.5 text-sm bg-white/10 rounded hover:bg-white/20">+</button>
        </div>
      </div>
    </div>
  );
}
