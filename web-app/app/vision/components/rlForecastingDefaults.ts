// Pre-populated demo data for the RL Forecasting tab so every chart has
// something visible on first paint, even if the inventory-rl service is
// still booting (or offline). Live API responses overwrite these once
// they arrive.
//
// Numbers are hand-tuned to look like a healthy trained-RL run on the 30-
// day single-product env: ~25 reward/episode, ~93% service level, a
// couple of stockout days (so the daily-rewards chart has 1-2 red bars
// — pure perfection looks fake). Heatmap is centered on the 30-70
// inventory band per day with a peak ~25 visits.

import type {
  RLPrediction, RLSimulateResult, RLCompareResult,
} from "../lib/api";

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// 30 days of synthetic per-day data. Designed to hit *exactly* 3
// "miss" days (red reward bars + sold visibly below demand) so the demo
// charts read true to a real-but-good RL run rather than implausibly
// perfect. Misses are at days 9, 17, 27 (Sundays where inventory was
// drained low before the demand spike).
const RL_DAYS = (() => {
  type Day = {
    day: number; day_of_week: string;
    inventory_start: number; order_qty: number;
    demand: number; sold: number; unmet_demand: number;
    inventory_end: number; reward: number;
  };
  const days: Day[] = [];
  let inv = 100;
  // Miss days (0-indexed). We force inventory low at the start of these
  // days and skip the order so demand outstrips supply.
  const MISS_DAYS = new Set<number>([8, 16, 26]);

  for (let d = 0; d < 30; d++) {
    const dow = d % 7;
    const baseDemand =
      dow < 5 ? 6 + Math.round(Math.sin(d * 0.7) * 4)            // weekday 2-12
      : dow === 5 ? 24 + (d % 5)                                  // saturday 24-28
      : 42 + (d % 6);                                              // sunday 42-47
    const trended = baseDemand + Math.floor(d / 8);

    // On miss days, drain the carryover inventory to a small fixed value
    // (8 units) so `inventory + order = 8` is well below the 30-50 demand
    // → guaranteed stockout. Sold will be 8, demand 40+, so blue dot sits
    // far below orange — visible on the chart.
    if (MISS_DAYS.has(d)) inv = 8;

    let order =
      inv < 30 ? 30 + (dow >= 4 ? 15 : 0)
      : inv < 55 ? 15 + (dow === 4 ? 10 : 0)
      : 0;
    if (MISS_DAYS.has(d)) order = 0;

    const startInv = inv;
    const afterOrder = inv + order;
    const sold = Math.min(afterOrder, trended);
    const unmet = Math.max(0, trended - afterOrder);
    const endInv = afterOrder - sold;
    const reward = (unmet === 0 && endInv > 0 && endInv <= 100) ? 1 : -1;
    days.push({
      day: d + 1,
      day_of_week: DOW[dow],
      inventory_start: startInv,
      order_qty: order,
      demand: trended,
      sold,
      unmet_demand: unmet,
      inventory_end: endInv,
      reward,
    });
    inv = endInv;
  }
  return days;
})();

// 10 per-episode rows with realistic spread. One negative episode at
// index 0 (an "early/unlucky" run) so the bar chart has a red bar and
// the policy looks earned rather than implausibly perfect. Mean ~22.
const RL_EPISODES = (() => {
  const base = [-4, 22, 24, 26, 25, 19, 27, 24, 26, 25];
  return base.map((r, i) => ({
    episode: i + 1,
    total_reward: r,
    stockout_days: Math.max(0, Math.round((30 - r) / 2)),
    overstock_days: 0,
    service_level: Math.max(40, 90 + (r - 22) * 0.8),
    avg_inventory: 44 + ((i * 3) % 9),
  }));
})();

// 10x10 visitation heatmap with a hot center pile in the 30-70 inventory
// band, scaled up to ~25 visits at the peak so the color ramp is visible.
// Rows = inventory bins (0-9 = 0-100 in steps of 10),
// cols = day bins (0-9 = days 0-29 in steps of 3).
const RL_HEATMAP = (() => {
  const grid: number[][] = Array.from({ length: 10 }, () => Array(10).fill(0));
  // Gaussian-ish pile centered at row 5 (inv 50-60), spread across all days.
  // Per-row baseline; per-col mild jitter.
  const rowWeights: Record<number, number> = {
    2: 2, 3: 6, 4: 13, 5: 22, 6: 14, 7: 7, 8: 3,
  };
  for (let row = 0; row < 10; row++) {
    const base = rowWeights[row] ?? 0;
    if (base === 0) continue;
    for (let col = 0; col < 10; col++) {
      const jitter = ((row + col) % 4) - 1;  // -1, 0, 1, 2
      grid[row][col] = Math.max(0, base + jitter);
    }
  }
  // A few outliers in low/high bands to show the policy occasionally
  // strays — keeps it from looking suspiciously perfect.
  grid[0][9] = 1;
  grid[1][2] = 2;
  grid[1][7] = 1;
  grid[9][0] = 1;
  grid[9][5] = 1;
  return grid;
})();

export const DEFAULT_PREDICTION: RLPrediction = {
  action: 6,
  order_quantity: 30,
  reasoning: "Inventory at 50 units with weekend approaching — order 30 to safely cover Sat/Sun demand.",
  inventory_status: "🟢 OPTIMAL: Good level",
  demand_forecast: "Saturday: Expect MEDIUM demand (15-30 units)",
  formatted_log: [
    "============================================================",
    "📦 REQUEST #demo [pre-populated]",
    "Day 0 (0)",
    "------------------------------",
    "🤖 DECISION (AI Model — synthetic preview):",
    "     🟢 OPTIMAL: Good level",
    "     📊 Saturday: Expect MEDIUM demand (15-30 units)",
    "     📦 ORDER: 30 units",
    "     💭 Reasoning: Medium order to prepare for upcoming demand.",
    "------------------------------",
    "  📊 DEBUG: Inv=50 | Obs=[0.5, 0.0, 0.0]",
    "============================================================",
  ].join("\n"),
};

export const DEFAULT_SIM: RLSimulateResult = {
  policy: "rl",
  policy_label: "Trained RL (preview)",
  episodes_run: 10,
  aggregate: {
    avg_total_reward: 21.4,
    avg_stockout_days: 3.1,
    avg_overstock_days: 0.0,
    avg_service_level: 91.2,
    avg_inventory: 47.4,
  },
  per_episode: RL_EPISODES,
  last_episode_days: RL_DAYS,
  used_model: false,
  notes: "Showing pre-populated preview data. Live results replace this once the RL service responds.",
  heatmap: RL_HEATMAP,
};

// Comparison: RL clearly wins on reward + service, EOQ middle, random worst.
export const DEFAULT_COMPARISON: RLCompareResult = {
  episodes: 10,
  seed: 42,
  rows: [
    {
      policy: "random",
      policy_label: "Random",
      used_model: false,
      aggregate: {
        avg_total_reward: -12.4,
        avg_stockout_days: 8.2,
        avg_overstock_days: 4.1,
        avg_service_level: 64.5,
        avg_inventory: 38.9,
      },
      per_episode_rewards: [-15, -10, -18, -8, -14, -11, -16, -9, -13, -10],
      notes: "",
    },
    {
      policy: "eoq",
      policy_label: "EOQ (Q≈35, reorder=40)",
      used_model: false,
      aggregate: {
        avg_total_reward: 12.8,
        avg_stockout_days: 3.6,
        avg_overstock_days: 1.0,
        avg_service_level: 84.1,
        avg_inventory: 42.5,
      },
      per_episode_rewards: [10, 14, 11, 13, 15, 9, 12, 14, 13, 17],
      notes: "",
    },
    {
      policy: "rl",
      policy_label: "Trained RL (preview)",
      used_model: false,
      aggregate: {
        avg_total_reward: 24.1,
        avg_stockout_days: 2.2,
        avg_overstock_days: 0.0,
        avg_service_level: 93.6,
        avg_inventory: 47.4,
      },
      per_episode_rewards: [22, 24, 23, 26, 25, 19, 27, 24, 26, 25],
      notes: "",
    },
  ],
};
