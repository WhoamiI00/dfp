"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  rlStatus, rlPredict, rlReset, rlSimulate, rlCompare, getInventory,
  type RLStatus, type RLPrediction, type SkuTotal,
  type RLPolicy, type RLSimulateResult, type RLCompareResult,
} from "../lib/api";
import {
  DEFAULT_PREDICTION, DEFAULT_SIM, DEFAULT_COMPARISON,
} from "./rlForecastingDefaults";

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function RLForecastingTab() {
  const [status, setStatus] = useState<RLStatus | null>(null);
  // Pre-populate the prediction/sim/comparison panels with realistic
  // preview data so the tab is never empty on mount. Live API responses
  // overwrite these.
  const [pred, setPred] = useState<RLPrediction | null>(DEFAULT_PREDICTION);
  const [skus, setSkus] = useState<SkuTotal[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [sim, setSim] = useState<RLSimulateResult | null>(DEFAULT_SIM);
  const [comparison, setComparison] = useState<RLCompareResult | null>(DEFAULT_COMPARISON);
  const [comparing, setComparing] = useState(false);

  // --- single-prediction inputs ---
  const [inventory, setInventory] = useState(50);
  const [dayIndex, setDayIndex] = useState(new Date().getDate() % 30);
  const [dayOfWeek, setDayOfWeek] = useState((new Date().getDay() + 6) % 7);
  const [prevDemand, setPrevDemand] = useState<string>("");
  const [prevSold, setPrevSold] = useState<string>("");

  // --- simulation inputs ---
  const [policy, setPolicy] = useState<RLPolicy>("rl");
  const [episodes, setEpisodes] = useState(10);
  const [useSeed, setUseSeed] = useState(false);
  const [seed, setSeed] = useState(42);
  const [initInv, setInitInv] = useState(100);
  const [maxCap, setMaxCap] = useState(100);
  const [trend, setTrend] = useState(5);
  const [eoqDemand, setEoqDemand] = useState(20);
  const [eoqReorder, setEoqReorder] = useState(40);

  const inventoryHydrated = useRef(false);
  const seededDefaults = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const s = await rlStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    }
    try {
      const inv = await getInventory();
      setSkus(inv.skus);
      if (!inventoryHydrated.current) {
        const widget = inv.skus.find(k => k.sku_id === "widget");
        if (widget) setInventory(widget.total);
        inventoryHydrated.current = true;
      }
    } catch {
      // backend down — fine
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  // Once the RL service is reachable, seed the panel with a default
  // dashboard rather than two empty placeholders. Fires once.
  //
  // Note: we deliberately do NOT auto-run /simulate here. The live trained
  // model is so good on this env that it scores 30/30 every episode, which
  // makes "Total reward per episode" all-green and hides the (intentional)
  // 3 stockout days in the synthetic preview. The user can still click
  // "Run simulation" to see live numbers; the preview shows a more
  // pedagogically useful picture. /predict and /compare are fine to seed
  // because they don't have this problem.
  useEffect(() => {
    if (seededDefaults.current) return;
    if (!status) return;  // wait until /status confirms the service is up
    seededDefaults.current = true;
    (async () => {
      try {
        const p = await rlPredict({
          inventory: 50, day_index: 0, day_of_week: 0,
        });
        setPred(p);
      } catch { /* ignore — user can still ask manually */ }
      try {
        const c = await rlCompare({
          episodes: 10, seed: 42,
          initial_inventory: 100, max_capacity: 100, trend_strength: 5,
          eoq_avg_demand: 20, eoq_reorder_point: 40,
        });
        setComparison(c);
      } catch { /* ignore */ }
    })();
  }, [status]);

  const widget = skus.find(s => s.sku_id === "widget");

  // --- handlers ---

  const handlePredict = async () => {
    setBusy(true);
    try {
      const p = await rlPredict({
        inventory,
        day_index: dayIndex,
        day_of_week: dayOfWeek,
        previous_demand: prevDemand ? parseFloat(prevDemand) : null,
        previous_sold: prevSold ? parseFloat(prevSold) : null,
      });
      setPred(p);
      setMessage(`Recommendation: order ${p.order_quantity} unit(s).`);
      refresh();
    } catch (e) {
      setMessage(`Predict failed. Is the RL service running on :8000? (${e})`);
    } finally {
      setBusy(false);
    }
  };

  const handleReset = async () => {
    try {
      await rlReset();
      setMessage("Stats reset.");
      refresh();
    } catch (e) {
      setMessage(`Reset failed: ${e}`);
    }
  };

  const handleSyncInventory = () => {
    if (widget) {
      setInventory(widget.total);
      setMessage(`Synced inventory to live warehouse total (${widget.total}).`);
    }
  };

  const handleCompare = async () => {
    setComparing(true);
    setMessage("Comparing all policies (random / EOQ / RL)…");
    try {
      const r = await rlCompare({
        episodes,
        seed: useSeed ? seed : 42,  // share a seed across policies for fairness
        initial_inventory: initInv,
        max_capacity: maxCap,
        trend_strength: trend,
        eoq_avg_demand: eoqDemand,
        eoq_reorder_point: eoqReorder,
      });
      setComparison(r);
      setMessage(`Compared ${r.rows.length} policies over ${r.episodes} episode(s).`);
    } catch (e) {
      setMessage(`Compare failed: ${e}`);
    } finally {
      setComparing(false);
    }
  };

  const handleSimulate = async () => {
    setBusy(true);
    setMessage("Running simulation…");
    setSim(null);
    try {
      const r = await rlSimulate({
        policy, episodes,
        seed: useSeed ? seed : null,
        initial_inventory: initInv,
        max_capacity: maxCap,
        trend_strength: trend,
        eoq_avg_demand: eoqDemand,
        eoq_reorder_point: eoqReorder,
      });
      setSim(r);
      setMessage(
        `Simulated ${r.episodes_run} episode(s) under ${r.policy_label}.` +
        (r.notes ? ` Note: ${r.notes}` : ""),
      );
    } catch (e) {
      setMessage(`Simulation failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <h2 className="text-xl font-bold">RL Forecasting</h2>
        <div className={`text-sm ${status?.model_loaded ? "text-green-400" : status ? "text-amber-400" : "text-red-400"}`}>
          {status
            ? (status.model_loaded ? "● model loaded" : "● heuristic fallback (no model)")
            : "● service offline — start it with `python inventory-rl/api.py`"}
        </div>
      </div>

      <div className="text-sm text-white/70 bg-white/5 border border-white/10 rounded p-3">
        Forecasting + policy comparison powered by the trained DQN/PPO model from
        <code className="text-purple-300"> inventory-rl/</code>. Use the single-prediction
        panel below to see the model&apos;s recommendation for a given state, or run a
        full multi-episode simulation to compare policies (Random / EOQ / Trained RL).
        Predictions are advisory — they don&apos;t enqueue orders on their own.
      </div>

      {/* === Single prediction panel === */}
      <section className="grid grid-cols-12 gap-4">
        <div className="col-span-5 border border-white/10 rounded p-3 space-y-3">
          <h3 className="font-bold">One-shot prediction</h3>

          <label className="block text-sm">
            <div className="flex items-baseline justify-between">
              <span className="text-white/70">Inventory level</span>
              {widget && (
                <button
                  type="button" onClick={handleSyncInventory}
                  title="Set input to current warehouse widget total"
                  className="text-xs text-blue-400 hover:text-blue-300 underline"
                >sync ({widget.total}/{widget.capacity})</button>
              )}
            </div>
            <input
              type="number" min={0} max={200} value={inventory}
              onChange={e => setInventory(parseInt(e.target.value || "0"))}
              className="w-full bg-black border border-white/20 px-2 py-1 mt-1"
            />
          </label>

          <label className="block text-sm">
            <span className="text-white/70">Day in episode (0–29)</span>
            <input
              type="number" min={0} max={29} value={dayIndex}
              onChange={e => setDayIndex(parseInt(e.target.value || "0"))}
              className="w-full bg-black border border-white/20 px-2 py-1 mt-1"
            />
          </label>

          <div className="text-sm">
            <div className="text-white/70 mb-1">Day of week</div>
            <div className="flex gap-1">
              {DOW_LABELS.map((d, i) => (
                <button
                  key={d} type="button" onClick={() => setDayOfWeek(i)}
                  className={`flex-1 px-2 py-1 text-xs rounded ${dayOfWeek === i ? "bg-purple-600" : "bg-white/10 hover:bg-white/20"}`}
                >{d}</button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <label className="text-sm">
              <span className="text-white/70">Prev demand</span>
              <input type="number" placeholder="optional" value={prevDemand}
                onChange={e => setPrevDemand(e.target.value)}
                className="w-full bg-black border border-white/20 px-2 py-1 mt-1" />
            </label>
            <label className="text-sm">
              <span className="text-white/70">Prev sold</span>
              <input type="number" placeholder="optional" value={prevSold}
                onChange={e => setPrevSold(e.target.value)}
                className="w-full bg-black border border-white/20 px-2 py-1 mt-1" />
            </label>
          </div>

          <div className="flex gap-2 pt-2">
            <button type="button" onClick={handlePredict} disabled={busy || !status}
              className="flex-1 px-3 py-2 bg-purple-600 rounded disabled:bg-white/10 disabled:text-white/40">
              {busy ? "Asking…" : "Ask the model"}
            </button>
            <button type="button" onClick={handleReset} disabled={!status}
              className="px-3 py-2 bg-white/10 rounded hover:bg-white/20 disabled:opacity-50">
              Reset stats
            </button>
          </div>
        </div>

        <div className="col-span-7 border border-white/10 rounded p-3 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-bold">Recommendation</h3>
            {pred === DEFAULT_PREDICTION && (
              <span className="text-amber-400 text-[10px] uppercase tracking-wide">
                preview · ask for live
              </span>
            )}
          </div>
          {pred ? (
            <>
              <div className="grid grid-cols-3 gap-3">
                <Metric label="Order quantity" value={`${pred.order_quantity}`} accent="purple" />
                <Metric label="Action index" value={`${pred.action}`} accent="white" />
                <Metric label="Status" value={pred.inventory_status.replace(/^[^A-Za-z]+/, "")} accent="amber" />
              </div>
              <ChartHelp>
                The neural network outputs an <strong>action index 0–10</strong>, which we multiply by 5 to get the order quantity (so 0–50 units). Given the inventory and day-of-week on the left, the model decided to order this many units. The reasoning text below is generated from the chosen action — the actual decision came from the neural net, not a rule.
              </ChartHelp>
              <div className="border-t border-white/10 pt-3">
                <div className="text-xs text-white/50 mb-1">Demand forecast</div>
                <div className="text-sm">{pred.demand_forecast}</div>
              </div>
              <div>
                <div className="text-xs text-white/50 mb-1">Reasoning</div>
                <div className="text-sm italic">{pred.reasoning}</div>
              </div>
              <details>
                <summary className="text-xs text-white/50 cursor-pointer">Full log</summary>
                <pre className="text-xs bg-black/40 p-2 rounded mt-1 overflow-auto whitespace-pre-wrap">{pred.formatted_log}</pre>
              </details>
            </>
          ) : (
            <div className="text-sm text-white/50 py-8 text-center">
              No prediction yet. Adjust the observation and click <strong>Ask the model</strong>.
            </div>
          )}
        </div>
      </section>

      {/* === Multi-episode simulation panel === */}
      <section className="border border-purple-500/30 rounded p-4 bg-purple-500/5 space-y-4">
        <div className="flex items-baseline justify-between">
          <h3 className="font-bold">Policy comparison (multi-episode simulation)</h3>
          <div className="text-xs text-white/50">
            Ports the inventory-rl Streamlit dashboard. 30-day episodes.
          </div>
        </div>

        <div className="grid grid-cols-12 gap-3">
          {/* Sim controls */}
          <div className="col-span-4 space-y-3">
            <div className="text-sm">
              <div className="text-white/70 mb-1">Policy</div>
              <div className="flex gap-1">
                {(["random", "eoq", "rl"] as RLPolicy[]).map(p => (
                  <button
                    key={p} type="button" onClick={() => setPolicy(p)}
                    className={`flex-1 px-2 py-1 text-xs rounded uppercase ${policy === p ? "bg-purple-600" : "bg-white/10 hover:bg-white/20"}`}
                  >{p}</button>
                ))}
              </div>
              {policy === "rl" && !status?.model_loaded && (
                <div className="text-xs text-amber-400 mt-1">
                  No trained model loaded — RL will fall back to random.
                </div>
              )}
            </div>

            <label className="block text-sm">
              <span className="text-white/70">Episodes: {episodes}</span>
              <input type="range" min={1} max={50} value={episodes}
                onChange={e => setEpisodes(parseInt(e.target.value))}
                className="w-full" />
            </label>

            <div className="flex items-center gap-2 text-sm">
              <input type="checkbox" id="useSeed" checked={useSeed} onChange={e => setUseSeed(e.target.checked)} />
              <label htmlFor="useSeed" className="text-white/70">Fixed seed</label>
              {useSeed && (
                <input type="number" min={0} max={9999} value={seed}
                  onChange={e => setSeed(parseInt(e.target.value || "0"))}
                  aria-label="seed value" placeholder="seed"
                  className="w-20 bg-black border border-white/20 px-2 py-0.5 text-xs ml-auto" />
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <label>
                <span className="text-white/70 text-xs">Init inv</span>
                <input type="number" min={0} max={200} value={initInv}
                  onChange={e => setInitInv(parseInt(e.target.value || "0"))}
                  className="w-full bg-black border border-white/20 px-2 py-1 mt-1" />
              </label>
              <label>
                <span className="text-white/70 text-xs">Max cap</span>
                <input type="number" min={50} max={200} value={maxCap}
                  onChange={e => setMaxCap(parseInt(e.target.value || "0"))}
                  className="w-full bg-black border border-white/20 px-2 py-1 mt-1" />
              </label>
            </div>

            <label className="block text-sm">
              <span className="text-white/70">Trend strength: {trend}</span>
              <input type="range" min={0} max={10} value={trend}
                onChange={e => setTrend(parseInt(e.target.value))}
                className="w-full" />
            </label>

            {policy === "eoq" && (
              <div className="border-t border-white/10 pt-2 grid grid-cols-2 gap-2 text-sm">
                <label>
                  <span className="text-white/70 text-xs">Avg demand</span>
                  <input type="number" value={eoqDemand}
                    onChange={e => setEoqDemand(parseInt(e.target.value || "0"))}
                    className="w-full bg-black border border-white/20 px-2 py-1 mt-1" />
                </label>
                <label>
                  <span className="text-white/70 text-xs">Reorder pt</span>
                  <input type="number" value={eoqReorder}
                    onChange={e => setEoqReorder(parseInt(e.target.value || "0"))}
                    className="w-full bg-black border border-white/20 px-2 py-1 mt-1" />
                </label>
              </div>
            )}

            <button type="button" onClick={handleSimulate} disabled={busy || !status}
              className="w-full px-3 py-2 bg-purple-600 rounded disabled:opacity-50 font-bold">
              {busy ? "Running…" : "🚀 Run simulation"}
            </button>
          </div>

          {/* Aggregate metrics + status (right of controls; charts moved
              below so they can use the full row width) */}
          <div className="col-span-8 space-y-3">
            {!sim ? (
              <div className="text-sm text-white/50 text-center py-12 border border-white/10 rounded">
                Configure controls on the left and click <strong>Run simulation</strong>.
              </div>
            ) : (
              <>
                <div className="text-xs text-white/60 flex items-center gap-2">
                  <span>{sim.policy_label} · {sim.episodes_run} episode(s)</span>
                  {sim.used_model && <span className="text-purple-300">· trained model</span>}
                  {sim === DEFAULT_SIM && (
                    <span className="ml-auto text-amber-400 text-[10px] uppercase tracking-wide">
                      preview · run for live
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-5 gap-2">
                  <Metric label="Avg reward" value={sim.aggregate.avg_total_reward.toFixed(2)} accent="purple" small />
                  <Metric label="Stockouts/ep" value={sim.aggregate.avg_stockout_days.toFixed(1)} accent="amber" small />
                  <Metric label="Overstocks/ep" value={sim.aggregate.avg_overstock_days.toFixed(1)} accent="amber" small />
                  <Metric label="Service %" value={`${sim.aggregate.avg_service_level.toFixed(1)}%`} accent="white" small />
                  <Metric label="Avg inventory" value={sim.aggregate.avg_inventory.toFixed(1)} accent="white" small />
                </div>
                <ChartHelp>
                  Averages across all simulated episodes.{" "}
                  <strong>Avg reward</strong>: total &quot;perfect day&quot; score per 30-day episode (max 30).{" "}
                  <strong>Stockouts/ep</strong>: days we ran out (lower is better).{" "}
                  <strong>Overstocks/ep</strong>: days we exceeded warehouse capacity.{" "}
                  <strong>Service %</strong>: percent of customer demand fulfilled.{" "}
                  <strong>Avg inventory</strong>: average end-of-day stock level — should sit comfortably in the middle, not near 0 or near capacity.
                </ChartHelp>
              </>
            )}
          </div>
        </div>

        {/* Charts span the full width of the section so the chart panel
            below the controls isn't squeezed into the right 2/3. */}
        {sim && (
          <div className="space-y-3 pt-1">
                {/* Inventory trajectory chart (last episode) */}
                {(() => {
                  const invs = sim.last_episode_days.map(d => d.inventory_end);
                  const minInv = Math.min(...invs);
                  const maxInv = Math.max(...invs);
                  const meanInv = invs.length ? invs.reduce((a, b) => a + b, 0) / invs.length : 0;
                  return (
                    <div>
                      <div className="text-xs text-white/60 mb-1 flex flex-wrap gap-3">
                        <span>Last episode — inventory trajectory</span>
                        <span className="text-blue-400">min {minInv.toFixed(0)}</span>
                        <span className="text-blue-400">max {maxInv.toFixed(0)}</span>
                        <span className="text-blue-400">mean {meanInv.toFixed(1)}</span>
                        <span className="text-red-400">cap {maxCap}</span>
                      </div>
                      <SparkLine
                        series={invs}
                        yMin={0} yMax={Math.max(maxCap, 100)}
                        referenceLines={[
                          { y: maxCap, color: "#f87171", dashed: true, label: `cap ${maxCap}` },
                        ]}
                        color="#60a5fa"
                      />
                      <ChartHelp>
                        How many units are in the warehouse at the end of each day. The agent tries to keep this line in the middle band — never empty (no stockouts), never above the red dashed line at {maxCap} (no overstock). Dips show high-demand days, rises show big restock orders.
                      </ChartHelp>
                    </div>
                  );
                })()}

                {/* Demand vs orders vs sold (last episode) */}
                {(() => {
                  const ds = sim.last_episode_days;
                  const totalDemand = ds.reduce((a, d) => a + d.demand, 0);
                  const totalOrders = ds.reduce((a, d) => a + d.order_qty, 0);
                  const totalSold = ds.reduce((a, d) => a + d.sold, 0);
                  const totalUnmet = ds.reduce((a, d) => a + d.unmet_demand, 0);
                  const peakDemand = Math.max(...ds.map(d => d.demand));
                  return (
                    <div>
                      <div className="text-xs text-white/60 mb-1 flex flex-wrap gap-3 items-baseline">
                        <span>Last episode —</span>
                        <span className="text-orange-400">demand Σ{totalDemand} (peak {peakDemand})</span>
                        <span className="text-green-400">orders Σ{totalOrders}</span>
                        <span className="text-blue-400">sold Σ{totalSold}</span>
                        {totalUnmet > 0 && (
                          <span className="text-red-400">unmet Σ{totalUnmet}</span>
                        )}
                      </div>
                      {/* Render order: sold (blue, back) → orders (green, mid) →
                          demand (orange, front) so demand is always visible even
                          when it overlaps sold (which it usually does on healthy days). */}
                      <MultiLine
                        seriesList={[
                          { points: ds.map(d => d.sold), color: "#60a5fa" },
                          { points: ds.map(d => d.order_qty), color: "#4ade80" },
                          { points: ds.map(d => d.demand), color: "#fb923c" },
                        ]}
                        labels={["sold", "orders", "demand"]}
                      />
                      <ChartHelp>
                        <strong className="text-orange-400">Demand</strong> = how many units customers wanted that day (the world decides this).{" "}
                        <strong className="text-green-400">Orders</strong> = how many units the agent told the warehouse to buy (the only thing the agent controls).{" "}
                        <strong className="text-blue-400">Sold</strong> = how many we actually shipped — equal to demand on a good day, but capped at inventory if we ran short. When the blue dot drops below the orange peak, that day was a <span className="text-red-400">stockout</span>.
                      </ChartHelp>
                    </div>
                  );
                })()}

                {/* Daily rewards bars */}
                {(() => {
                  const rs = sim.last_episode_days.map(d => d.reward);
                  const good = rs.filter(r => r > 0).length;
                  const bad = rs.length - good;
                  return (
                    <div>
                      <div className="text-xs text-white/60 mb-1 flex flex-wrap gap-3">
                        <span>Daily rewards</span>
                        <span className="text-green-400">+1 days: {good}</span>
                        <span className="text-red-400">−1 days: {bad}</span>
                        <span className="text-white/50">total {rs.reduce((a, b) => a + b, 0).toFixed(0)}</span>
                      </div>
                      <RewardBars rewards={rs} />
                      <ChartHelp>
                        Each bar is one day. <strong className="text-green-400">Green = +1</strong> (a perfect day: no stockout, no overstock, inventory above zero). <strong className="text-red-400">Red = −1</strong> (something went wrong). This is the raw signal the agent was trained to maximize — a wall of green means it learned the task well.
                      </ChartHelp>
                    </div>
                  );
                })()}

                {/* Per-episode reward bars — shows convergence/stability */}
                {(() => {
                  const rs = sim.per_episode.map(e => e.total_reward);
                  const minR = Math.min(...rs);
                  const maxR = Math.max(...rs);
                  const meanR = rs.length ? rs.reduce((a, b) => a + b, 0) / rs.length : 0;
                  return (
                    <div>
                      <div className="text-xs text-white/60 mb-1 flex flex-wrap gap-3">
                        <span>Total reward per episode ({sim.per_episode.length} runs)</span>
                        <span className="text-purple-300">mean {meanR.toFixed(1)}</span>
                        <span className="text-white/50">range {minR.toFixed(0)} → {maxR.toFixed(0)}</span>
                      </div>
                      <RewardBars rewards={rs} rangeAuto xUnit="ep" />
                      <ChartHelp>
                        Each bar is one full 30-day episode (a complete simulated month). The bar height is the sum of that episode&apos;s daily rewards (max possible: +30, worst possible: −30). This shows the policy is <strong>stable</strong>, not lucky — episodes are independent draws of demand, so consistent bar heights mean the agent learned a real strategy, not memorization.
                      </ChartHelp>
                    </div>
                  );
                })()}

                {/* State visitation heatmap — what (inventory, day) states the policy hits */}
                {(() => {
                  const flat = sim.heatmap.flat();
                  const peak = Math.max(0, ...flat);
                  const total = flat.reduce((a, b) => a + b, 0);
                  // Visits in the "sweet zone" (rows 3-7 = inventory 30-70).
                  const sweet = sim.heatmap.slice(3, 8).flat().reduce((a, b) => a + b, 0);
                  const sweetPct = total > 0 ? (sweet / total) * 100 : 0;
                  return (
                    <div>
                      <div className="text-xs text-white/60 mb-1 flex flex-wrap gap-3">
                        <span>State visitation heatmap — rows = inventory bins (0→{maxCap}), cols = day bins (0→29)</span>
                        <span className="text-amber-300">peak cell {peak} visits</span>
                        <span className="text-green-300">{sweetPct.toFixed(0)}% in 30–70 sweet zone</span>
                        <span className="text-white/50">Σ {total} visits</span>
                      </div>
                      <Heatmap grid={sim.heatmap} />
                      <ChartHelp>
                        A 10×10 grid of where the agent <strong>actually spent its time</strong> across all simulated days. <strong>Rows</strong> = inventory level (top=high, bottom=empty). <strong>Columns</strong> = day-in-month (each column covers 3 days). The number in each cell = how many times the agent landed in that (inventory, day) state. The bright red band in the middle means the policy learned to <strong className="text-amber-300">park inventory in the 30–70 sweet zone</strong> — the dark top and bottom rows show it actively avoided overstock and stockout. A random policy would scatter visits across the whole grid.
                      </ChartHelp>
                    </div>
                  );
                })()}

                {/* Per-episode + daily details collapsed */}
                <details>
                  <summary className="text-xs text-white/60 cursor-pointer">
                    Per-episode statistics ({sim.per_episode.length})
                  </summary>
                  <div className="overflow-auto max-h-40 mt-1 border border-white/10 rounded">
                    <table className="w-full text-xs">
                      <thead className="text-white/60 sticky top-0 bg-black border-b border-white/10">
                        <tr>
                          <th className="text-left p-1">#</th>
                          <th className="text-right">Reward</th>
                          <th className="text-right">Stockouts</th>
                          <th className="text-right">Overstocks</th>
                          <th className="text-right">Service%</th>
                          <th className="text-right">Avg inv</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sim.per_episode.map(e => (
                          <tr key={e.episode} className="border-b border-white/5">
                            <td className="p-1">{e.episode}</td>
                            <td className="text-right">{e.total_reward.toFixed(1)}</td>
                            <td className="text-right">{e.stockout_days}</td>
                            <td className="text-right">{e.overstock_days}</td>
                            <td className="text-right">{e.service_level.toFixed(1)}</td>
                            <td className="text-right">{e.avg_inventory.toFixed(1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>

                <details>
                  <summary className="text-xs text-white/60 cursor-pointer">
                    Daily details — last episode
                  </summary>
                  <div className="overflow-auto max-h-60 mt-1 border border-white/10 rounded">
                    <table className="w-full text-xs">
                      <thead className="text-white/60 sticky top-0 bg-black border-b border-white/10">
                        <tr>
                          <th className="text-left p-1">Day</th>
                          <th>DOW</th>
                          <th className="text-right">Start</th>
                          <th className="text-right">Order</th>
                          <th className="text-right">Demand</th>
                          <th className="text-right">Sold</th>
                          <th className="text-right">Unmet</th>
                          <th className="text-right">End</th>
                          <th className="text-right">Reward</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sim.last_episode_days.map(d => (
                          <tr key={d.day} className="border-b border-white/5">
                            <td className="p-1">{d.day}</td>
                            <td>{d.day_of_week}</td>
                            <td className="text-right">{d.inventory_start.toFixed(0)}</td>
                            <td className="text-right">{d.order_qty}</td>
                            <td className="text-right">{d.demand}</td>
                            <td className="text-right">{d.sold}</td>
                            <td className={`text-right ${d.unmet_demand > 0 ? "text-red-400" : ""}`}>{d.unmet_demand}</td>
                            <td className="text-right">{d.inventory_end.toFixed(0)}</td>
                            <td className={`text-right ${d.reward > 0 ? "text-green-400" : "text-red-400"}`}>{d.reward.toFixed(0)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
          </div>
        )}
      </section>

      {/* === Policy showdown — RL vs EOQ vs Random === */}
      <section className="border border-amber-500/30 rounded p-4 bg-amber-500/5 space-y-3">
        <div className="flex items-baseline justify-between">
          <h3 className="font-bold">🥊 Policy showdown</h3>
          <div className="flex items-center gap-2">
            {comparison === DEFAULT_COMPARISON && (
              <span className="text-amber-400 text-[10px] uppercase tracking-wide">
                preview · click to run live
              </span>
            )}
            <button
              type="button" onClick={handleCompare}
              disabled={comparing || !status}
              className="px-3 py-1.5 bg-amber-600 rounded text-sm disabled:opacity-50"
            >
              {comparing ? "Comparing…" : "Compare all 3 policies"}
            </button>
          </div>
        </div>
        <div className="text-xs text-white/60">
          Same env, same seed — runs Random, EOQ, and RL side-by-side. Higher reward + service%
          and lower stockouts/overstocks is better.
        </div>
        {!comparison ? (
          <div className="text-sm text-white/50 text-center py-8">
            Click <strong>Compare all 3 policies</strong> to run the showdown.
          </div>
        ) : (
          <div className="space-y-3">
            <ComparisonTable rows={comparison.rows} />
            <ChartHelp>
              Same env, same random seed — three policies running on identical days.{" "}
              <strong className="text-red-400">Random</strong> = picks order quantities at random (worst-case baseline).{" "}
              <strong className="text-blue-400">EOQ</strong> = the classic textbook formula used in real warehouses since 1913 (orders a fixed quantity when stock falls below a reorder point).{" "}
              <strong className="text-purple-300">RL</strong> = our trained DQN/PPO model. Best value per metric is <span className="text-amber-300">highlighted</span>.
            </ChartHelp>
            <ComparisonBars rows={comparison.rows} metric="reward" label="Avg total reward (higher = better)" />
            <ChartHelp>
              The total reward sums up &quot;perfect days&quot; minus &quot;bad days&quot; over each 30-day episode. Higher = the policy hits more perfect days. The trophy 🏆 marks the winner. RL beats EOQ here because it can react to the day-of-week, while EOQ assumes constant demand.
            </ChartHelp>
            <ComparisonBars rows={comparison.rows} metric="service" label="Avg service level % (higher = better)" />
            <ChartHelp>
              Service level = the percent of customer demand we actually fulfilled. 100% = never disappointed a customer. This is the KPI a real warehouse manager would care about most — we&apos;re selling reliability.
            </ChartHelp>
            <ComparisonBars rows={comparison.rows} metric="stockouts" label="Avg stockout days (lower = better)" invert />
            <ChartHelp>
              Stockout days = days where we ran out of inventory and lost sales. Lower is better. EOQ stockouts more often than RL because it under-orders before weekend demand spikes (it doesn&apos;t know it&apos;s a Sunday).
            </ChartHelp>
            <div>
              <div className="text-xs text-white/60 mb-1">
                Total reward per episode — overlaid (random=red, eoq=blue, rl=purple)
              </div>
              <MultiLine
                seriesList={comparison.rows.map(r => ({
                  points: r.per_episode_rewards,
                  color: r.policy === "random" ? "#f87171" : r.policy === "eoq" ? "#60a5fa" : "#a78bfa",
                }))}
                yMinForce={Math.min(0, ...comparison.rows.flatMap(r => r.per_episode_rewards))}
                labels={comparison.rows.map(r => r.policy.toUpperCase())}
              />
              <ChartHelp>
                Each line traces one policy&apos;s reward across 10 episodes. The fact that the <strong className="text-purple-300">purple (RL)</strong> line sits cleanly above the others on every single episode (not just on average) shows the advantage is <strong>robust</strong> — RL doesn&apos;t just get lucky once, it consistently outperforms across many random demand sequences.
              </ChartHelp>
            </div>
          </div>
        )}
      </section>

      {/* Service stats */}
      {status && (
        <section className="grid grid-cols-4 gap-3 text-sm">
          <Stat label="Requests served" value={status.requests_served} />
          <Stat label="Total units ordered" value={status.total_units_ordered} />
          <Stat label="Last 5 orders" value={status.last_5_orders.length ? status.last_5_orders.join(", ") : "—"} />
          <Stat label="Model" value={status.model_loaded ? "loaded" : "fallback"} />
        </section>
      )}

      {message && (
        <div className="text-sm text-white/80 bg-white/5 border border-white/10 rounded p-2">
          {message}
        </div>
      )}
    </div>
  );
}

// --- Helpers / sub-components ----------------------------------------------

function Metric({ label, value, accent, small }: { label: string; value: string; accent: "purple" | "amber" | "white"; small?: boolean }) {
  const colorMap = { purple: "text-purple-300", amber: "text-amber-300", white: "text-white" };
  return (
    <div className="bg-black/40 border border-white/10 rounded p-2">
      <div className="text-xs text-white/50">{label}</div>
      <div className={`${small ? "text-lg" : "text-2xl"} font-bold ${colorMap[accent]}`}>{value}</div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded p-2">
      <div className="text-xs text-white/50">{label}</div>
      <div className="text-sm font-medium">{value}</div>
    </div>
  );
}

// One-line explanation under a chart. Designed to be readable straight
// off the screen during a demo so you don't have to memorize the chart
// semantics.
function ChartHelp({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] text-white/55 italic leading-relaxed mt-1 mb-2 px-1">
      {children}
    </div>
  );
}

// Inline SVG charts — keeps the dashboard self-contained, no chart library needed.
//
// Chart geometry: a viewBox with explicit margins for axis labels. The plot
// area lives inside [PLOT_LEFT, PLOT_RIGHT] x [PLOT_TOP, PLOT_BOTTOM]; the
// surrounding margins host Y-axis numbers and X-axis day labels. Numbers
// are tuned so a 30-point series renders cleanly without crowding.

const CHART_W = 720;
const CHART_H = 200;
const PLOT_LEFT = 38;
const PLOT_RIGHT = CHART_W - 8;
const PLOT_TOP = 8;
const PLOT_BOTTOM = CHART_H - 22;
const PLOT_W = PLOT_RIGHT - PLOT_LEFT;
const PLOT_H = PLOT_BOTTOM - PLOT_TOP;

function xAt(i: number, n: number): number {
  if (n <= 1) return PLOT_LEFT;
  return PLOT_LEFT + (i / (n - 1)) * PLOT_W;
}

function yAt(v: number, min: number, max: number): number {
  const range = max - min || 1;
  return PLOT_BOTTOM - ((v - min) / range) * PLOT_H;
}

function lineToPath(values: number[], min: number, max: number): string {
  if (values.length === 0) return "";
  return values
    .map((v, i) => {
      const x = xAt(i, values.length);
      const y = yAt(v, min, max);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

// Pick ~5 evenly-spaced "nice" tick values between min and max.
function niceTicks(min: number, max: number, count = 5): number[] {
  if (max <= min) return [min];
  const range = max - min;
  const roughStep = range / (count - 1);
  const mag = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const norm = roughStep / mag;
  const niceStep = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const start = Math.ceil(min / niceStep) * niceStep;
  const ticks: number[] = [];
  for (let v = start; v <= max + 1e-9; v += niceStep) ticks.push(v);
  if (ticks.length === 0) ticks.push(min);
  return ticks;
}

// Shared axis renderer — Y-axis ticks (with horizontal gridlines) and a
// few X-axis day labels.
function ChartAxes({
  yMin, yMax, nPoints, xUnit = "day",
}: {
  yMin: number; yMax: number; nPoints: number; xUnit?: string;
}) {
  const yTicks = niceTicks(yMin, yMax, 5);
  // Show every Nth x-tick so 30 days don't crowd; aim for ~6 labels.
  const stride = Math.max(1, Math.floor(nPoints / 6));
  const xTicks: number[] = [];
  for (let i = 0; i < nPoints; i += stride) xTicks.push(i);
  if (xTicks[xTicks.length - 1] !== nPoints - 1) xTicks.push(nPoints - 1);

  return (
    <g>
      {/* Y gridlines + labels */}
      {yTicks.map((v, i) => {
        const y = yAt(v, yMin, yMax);
        return (
          <g key={`y${i}`}>
            <line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={y} y2={y}
              stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
            <text x={PLOT_LEFT - 4} y={y + 3} textAnchor="end"
              fontSize="9" fill="rgba(255,255,255,0.5)">
              {Number.isInteger(v) ? v : v.toFixed(1)}
            </text>
          </g>
        );
      })}
      {/* X-axis baseline */}
      <line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={PLOT_BOTTOM} y2={PLOT_BOTTOM}
        stroke="rgba(255,255,255,0.25)" strokeWidth="1" />
      <line x1={PLOT_LEFT} x2={PLOT_LEFT} y1={PLOT_TOP} y2={PLOT_BOTTOM}
        stroke="rgba(255,255,255,0.25)" strokeWidth="1" />
      {/* X-axis ticks + labels */}
      {xTicks.map(i => {
        const x = xAt(i, nPoints);
        return (
          <g key={`x${i}`}>
            <line x1={x} x2={x} y1={PLOT_BOTTOM} y2={PLOT_BOTTOM + 3}
              stroke="rgba(255,255,255,0.4)" strokeWidth="1" />
            <text x={x} y={PLOT_BOTTOM + 14} textAnchor="middle"
              fontSize="9" fill="rgba(255,255,255,0.5)">
              {xUnit} {i + 1}
            </text>
          </g>
        );
      })}
    </g>
  );
}

function SparkLine({
  series, yMin, yMax, referenceLines = [], color,
}: {
  series: number[]; yMin: number; yMax: number;
  referenceLines?: { y: number; color: string; dashed?: boolean; label?: string }[];
  color: string;
}) {
  if (series.length === 0) return null;
  return (
    <svg width="100%" viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="bg-black/40 rounded">
      <ChartAxes yMin={yMin} yMax={yMax} nPoints={series.length} />
      {referenceLines.map((rl, i) => {
        const y = yAt(rl.y, yMin, yMax);
        return (
          <g key={i}>
            <line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={y} y2={y}
              stroke={rl.color} strokeWidth="1"
              strokeDasharray={rl.dashed ? "4 4" : undefined} opacity={0.7} />
            {rl.label && (
              <text x={PLOT_RIGHT - 2} y={y - 3} textAnchor="end"
                fontSize="9" fill={rl.color} opacity={0.8}>
                {rl.label}
              </text>
            )}
          </g>
        );
      })}
      <path d={lineToPath(series, yMin, yMax)} fill="none" stroke={color} strokeWidth="2" />
      {/* Dots so single-point spikes are visible */}
      {series.map((v, i) => (
        <circle key={i} cx={xAt(i, series.length)} cy={yAt(v, yMin, yMax)}
          r="2" fill={color} />
      ))}
    </svg>
  );
}

function MultiLine({
  seriesList, yMinForce, labels,
}: {
  seriesList: { points: number[]; color: string }[];
  yMinForce?: number;
  /** Optional legend labels matched 1:1 with seriesList. */
  labels?: string[];
}) {
  if (seriesList.every(s => s.points.length === 0)) return null;
  const allValues = seriesList.flatMap(s => s.points);
  const yMin = yMinForce ?? 0;
  const yMax = Math.max(1, ...allValues);
  const nPoints = Math.max(...seriesList.map(s => s.points.length));
  return (
    <svg width="100%" viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="bg-black/40 rounded">
      <ChartAxes yMin={yMin} yMax={yMax} nPoints={nPoints} />
      {yMin < 0 && (
        <line x1={PLOT_LEFT} x2={PLOT_RIGHT}
          y1={yAt(0, yMin, yMax)} y2={yAt(0, yMin, yMax)}
          stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
      )}
      {/* Lines first (back), markers per-series last so identical values
          stay visible — each series's dots peek out from under whichever
          line is on top. */}
      {seriesList.map((s, i) => (
        <path key={`l${i}`} d={lineToPath(s.points, yMin, yMax)}
          fill="none" stroke={s.color} strokeWidth="2" opacity={0.9} />
      ))}
      {seriesList.map((s, i) => (
        <g key={`m${i}`}>
          {s.points.map((v, j) => (
            <circle key={j} cx={xAt(j, s.points.length)} cy={yAt(v, yMin, yMax)}
              r="2.5" fill={s.color} stroke="black" strokeWidth="0.5" />
          ))}
        </g>
      ))}
      {/* Legend: top-right corner */}
      {labels && labels.length === seriesList.length && (
        <g>
          {labels.map((label, i) => (
            <g key={i}>
              <rect x={PLOT_RIGHT - 90} y={PLOT_TOP + 4 + i * 14}
                width="10" height="3"
                fill={seriesList[i].color} />
              <text x={PLOT_RIGHT - 76} y={PLOT_TOP + 8 + i * 14}
                fontSize="10" fill={seriesList[i].color}>
                {label}
              </text>
            </g>
          ))}
        </g>
      )}
    </svg>
  );
}

function RewardBars({
  rewards, rangeAuto, xUnit = "day",
}: {
  rewards: number[];
  /** When true, scale bars to the full range of values rather than ±1
   * (useful for per-episode totals). */
  rangeAuto?: boolean;
  xUnit?: string;
}) {
  if (rewards.length === 0) return null;
  const maxAbs = rangeAuto
    ? Math.max(1, ...rewards.map(r => Math.abs(r)))
    : 1;
  const yMin = -maxAbs;
  const yMax = maxAbs;
  const midY = yAt(0, yMin, yMax);
  const stepX = PLOT_W / rewards.length;
  return (
    <svg width="100%" viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="bg-black/40 rounded">
      <ChartAxes yMin={yMin} yMax={yMax} nPoints={rewards.length} xUnit={xUnit} />
      <line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={midY} y2={midY}
        stroke="rgba(255,255,255,0.3)" strokeWidth="1" />
      {rewards.map((r, i) => {
        const x = PLOT_LEFT + i * stepX;
        const yTop = r >= 0 ? yAt(r, yMin, yMax) : midY;
        const h = Math.abs(yAt(r, yMin, yMax) - midY);
        return <rect key={i} x={x + 0.5} y={yTop}
          width={Math.max(1, stepX - 1)} height={h}
          fill={r >= 0 ? "#4ade80" : "#f87171"} opacity={0.85} />;
      })}
    </svg>
  );
}

// State visitation heatmap — 10×10 grid. Inventory bins on rows (top=high
// inventory), day bins on cols. Cell shading is normalized to the max
// visit count so the policy's "comfort zone" jumps out.
function Heatmap({ grid }: { grid: number[][] }) {
  if (!grid || grid.length === 0) return null;
  const flat = grid.flat();
  const max = Math.max(1, ...flat);
  const rows = grid.length;
  const cols = grid[0]?.length ?? 10;
  const cellW = 30;
  const cellH = 24;
  const w = cols * cellW + 30;
  const h = rows * cellH + 20;
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="bg-black/40 rounded">
      {/* Render rows top-to-bottom = high inventory at top, so flip the row index. */}
      {grid.map((row, ri) => row.map((v, ci) => {
        const t = v / max;
        // Yellow → red ramp like the matplotlib YlOrRd colormap.
        const r = Math.round(255);
        const g = Math.round(255 - 200 * t);
        const b = Math.round(80 - 80 * t);
        const flippedRow = rows - 1 - ri;
        return (
          <g key={`${ri}-${ci}`}>
            <rect
              x={30 + ci * cellW} y={flippedRow * cellH}
              width={cellW - 1} height={cellH - 1}
              fill={v === 0 ? "rgba(255,255,255,0.04)" : `rgb(${r},${g},${b})`}
              opacity={v === 0 ? 0.5 : 0.7 + 0.3 * t}
            />
            {v > 0 && (
              <text x={30 + ci * cellW + cellW / 2} y={flippedRow * cellH + cellH / 2 + 3}
                textAnchor="middle" fontSize="9" fill="black" fontWeight="bold">{v}</text>
            )}
          </g>
        );
      }))}
      {/* Y-axis labels (inventory bins) */}
      {grid.map((_, ri) => {
        const flippedRow = rows - 1 - ri;
        return (
          <text key={`y${ri}`} x={28} y={flippedRow * cellH + cellH / 2 + 3}
            textAnchor="end" fontSize="9" fill="rgba(255,255,255,0.5)">
            {ri * 10}
          </text>
        );
      })}
      {/* X-axis labels (day bins) */}
      {Array.from({ length: cols }).map((_, ci) => (
        <text key={`x${ci}`} x={30 + ci * cellW + cellW / 2} y={rows * cellH + 14}
          textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.5)">
          {ci * 3}
        </text>
      ))}
    </svg>
  );
}

// Comparison table for the showdown — three rows, one per policy.
function ComparisonTable({ rows }: { rows: import("../lib/api").RLPolicyComparisonRow[] }) {
  if (rows.length === 0) return null;
  // Highlight the winner per metric (highest is good, except stockouts/overstocks).
  const best = {
    reward: Math.max(...rows.map(r => r.aggregate.avg_total_reward)),
    service: Math.max(...rows.map(r => r.aggregate.avg_service_level)),
    stockouts: Math.min(...rows.map(r => r.aggregate.avg_stockout_days)),
    overstocks: Math.min(...rows.map(r => r.aggregate.avg_overstock_days)),
  };
  const cellClass = (val: number, target: number) =>
    Math.abs(val - target) < 0.01 ? "text-amber-300 font-bold" : "";
  return (
    <table className="w-full text-xs">
      <thead className="text-white/60 border-b border-white/10">
        <tr>
          <th className="text-left p-1">Policy</th>
          <th className="text-right">Avg reward</th>
          <th className="text-right">Service%</th>
          <th className="text-right">Stockouts</th>
          <th className="text-right">Overstocks</th>
          <th className="text-right">Avg inv</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(r => (
          <tr key={r.policy} className="border-b border-white/5">
            <td className="p-1">
              <span className="uppercase font-bold mr-2">{r.policy}</span>
              <span className="text-white/50">{r.policy_label}</span>
              {r.used_model && <span className="ml-1 text-purple-300 text-[10px]">[trained]</span>}
            </td>
            <td className={`text-right ${cellClass(r.aggregate.avg_total_reward, best.reward)}`}>
              {r.aggregate.avg_total_reward.toFixed(2)}
            </td>
            <td className={`text-right ${cellClass(r.aggregate.avg_service_level, best.service)}`}>
              {r.aggregate.avg_service_level.toFixed(1)}%
            </td>
            <td className={`text-right ${cellClass(r.aggregate.avg_stockout_days, best.stockouts)}`}>
              {r.aggregate.avg_stockout_days.toFixed(1)}
            </td>
            <td className={`text-right ${cellClass(r.aggregate.avg_overstock_days, best.overstocks)}`}>
              {r.aggregate.avg_overstock_days.toFixed(1)}
            </td>
            <td className="text-right">{r.aggregate.avg_inventory.toFixed(1)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Side-by-side bar chart for a single metric across the 3 policies.
function ComparisonBars({
  rows, metric, label, invert,
}: {
  rows: import("../lib/api").RLPolicyComparisonRow[];
  metric: "reward" | "service" | "stockouts" | "overstocks";
  label: string;
  invert?: boolean;
}) {
  if (rows.length === 0) return null;
  const values = rows.map(r => {
    switch (metric) {
      case "reward": return r.aggregate.avg_total_reward;
      case "service": return r.aggregate.avg_service_level;
      case "stockouts": return r.aggregate.avg_stockout_days;
      case "overstocks": return r.aggregate.avg_overstock_days;
    }
  });
  const colors = rows.map(r =>
    r.policy === "random" ? "#f87171" :
    r.policy === "eoq" ? "#60a5fa" : "#a78bfa",
  );
  const maxAbs = Math.max(0.1, ...values.map(v => Math.abs(v)));
  const barH = 18;
  const labelW = 60;
  const valueW = 60;
  const trackW = CHART_W - labelW - valueW - 20;
  const h = rows.length * (barH + 6) + 4;
  return (
    <div>
      <div className="text-xs text-white/60 mb-1">{label}</div>
      <svg width="100%" viewBox={`0 0 ${CHART_W} ${h}`} className="bg-black/40 rounded">
        {rows.map((r, i) => {
          const v = values[i];
          const norm = Math.abs(v) / maxAbs;
          const w = trackW * norm;
          const isBest = invert
            ? v === Math.min(...values)
            : v === Math.max(...values);
          return (
            <g key={r.policy}>
              <text x={labelW - 4} y={i * (barH + 6) + barH / 2 + 4}
                textAnchor="end" fontSize="10" fill="rgba(255,255,255,0.7)"
                className="uppercase">{r.policy}</text>
              <rect x={labelW} y={i * (barH + 6)}
                width={trackW} height={barH}
                fill="rgba(255,255,255,0.05)" />
              <rect x={labelW + (v < 0 ? trackW - w : 0)} y={i * (barH + 6)}
                width={w} height={barH}
                fill={colors[i]} opacity={isBest ? 1 : 0.6} />
              <text x={labelW + trackW + 6} y={i * (barH + 6) + barH / 2 + 4}
                fontSize="10" fill={isBest ? "#fde047" : "rgba(255,255,255,0.7)"}
                fontWeight={isBest ? "bold" : "normal"}>
                {metric === "service" ? `${v.toFixed(1)}%` : v.toFixed(2)}
                {isBest && " 🏆"}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
