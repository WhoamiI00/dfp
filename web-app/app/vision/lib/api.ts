import type {
  Shelf, CalibrationStatus, RobotPose, Waypoint, PlanMetrics, Settings,
} from "./types";

const API_BASE = "http://localhost:8100/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw new Error(JSON.stringify(detail));
  }
  return res.json();
}

export async function getSettings(): Promise<Settings> {
  return request<Settings>("/settings");
}

export async function getShelves(): Promise<{ shelves: Shelf[] }> {
  return request<{ shelves: Shelf[] }>("/shelves");
}

export async function saveShelves(shelves: Shelf[]): Promise<void> {
  await request("/shelves", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ shelves }),
  });
}

export async function getCalibrationStatus(): Promise<CalibrationStatus> {
  return request<CalibrationStatus>("/calibration/status");
}

export async function calibrateIntrinsic(files: File[]): Promise<{ calibration_error_px: number; captured_images: number }> {
  const form = new FormData();
  files.forEach(f => form.append("files", f));
  return request("/calibration/intrinsic", { method: "POST", body: form });
}

export async function calibrateExtrinsic(): Promise<{ calibration_error_px: number }> {
  return request("/calibration/extrinsic", { method: "POST" });
}

export async function calibrateExtrinsicManual(
  cornerPixels: [number, number][],
): Promise<{ calibration_error_px: number }> {
  return request("/calibration/extrinsic/manual", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ corner_pixels: cornerPixels }),
  });
}

export async function calibrateSynthetic(): Promise<{
  ok: boolean;
  image_size: [number, number];
  focal_length_px: number;
  synthetic_camera_height_m: number;
}> {
  return request("/calibration/synthetic", { method: "POST" });
}

export async function capture(): Promise<{ image_base64: string }> {
  return request("/capture");
}

export type CameraMode = "live" | "test_image";

export async function getCameraMode(): Promise<{ mode: CameraMode }> {
  return request("/camera/mode");
}

export async function setCameraImage(file: File): Promise<{ mode: CameraMode }> {
  const form = new FormData();
  form.append("file", file);
  return request("/camera/image", { method: "POST", body: form });
}

export async function clearCameraImage(): Promise<{ mode: CameraMode }> {
  return request("/camera/image", { method: "DELETE" });
}

export async function detect(): Promise<{ robot_pose: RobotPose | null; reason: string | null; annotated_image_base64: string }> {
  return request("/detect", { method: "POST" });
}

export async function detectDebug(): Promise<{
  front_color_name: string;
  back_color_name: string;
  min_marker_area_px: number;
  front_largest_area_px: number;
  back_largest_area_px: number;
  front_centroid_px: [number, number] | null;
  back_centroid_px: [number, number] | null;
  mask_overlay_base64: string;
}> {
  return request("/detect/debug", { method: "POST" });
}

export type HsvBand = {
  h_min: number; s_min: number; v_min: number;
  h_max: number; s_max: number; v_max: number;
};

export type HsvSampleResult = {
  median_h: number;
  median_s: number;
  median_v: number;
  bands: HsvBand[];
};

export async function sampleHsv(pixelU: number, pixelV: number, patchSize = 5): Promise<HsvSampleResult> {
  return request("/hsv/sample", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ pixel_u: pixelU, pixel_v: pixelV, patch_size: patchSize }),
  });
}

export type CustomHsvEntry = { name: string; bands: HsvBand[] };

export async function listCustomHsvRanges(): Promise<{ entries: CustomHsvEntry[] }> {
  return request("/hsv/custom_ranges");
}

export async function upsertCustomHsvRange(name: string, bands: HsvBand[]): Promise<CustomHsvEntry> {
  return request(`/hsv/custom_ranges/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ bands }),
  });
}

export async function deleteCustomHsvRange(name: string): Promise<{ ok: boolean; removed: string }> {
  return request(`/hsv/custom_ranges/${encodeURIComponent(name)}`, { method: "DELETE" });
}


export type AutoDetectedShelf = {
  id: string;
  pixel_cx: number;
  pixel_cy: number;
  pixel_area: number;
  world_x_m: number;
  world_y_m: number;
};

export async function autoDetectShelves(body?: {
  marker_color?: string;
  max_count?: number;
  id_prefix?: string;
  approach_offset_m?: number;
  shelf_width_m?: number;
  shelf_length_m?: number;
  persist?: boolean;
}): Promise<{
  shelves: AutoDetectedShelf[];
  annotated_image_base64: string;
  persisted: boolean;
}> {
  return request("/layout/auto_detect", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export async function plan(body: { task: "navigate" | "pick_place"; source_shelf_id?: string; destination_shelf_id: string }): Promise<{
  waypoints: Waypoint[];
  annotated_image_base64: string;
  metrics: PlanMetrics;
}> {
  return request("/plan", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export type ExecuteCommandLog = { cmd: string; reply: string; elapsed_ms: number };

export async function executePlan(body: {
  task: "navigate" | "pick_place";
  source_shelf_id?: string;
  destination_shelf_id: string;
  port?: string;
  baud?: number;
}): Promise<{
  ok: boolean;
  chars_sent: number;
  sequence: string;
  log: ExecuteCommandLog[];
  error: string | null;
}> {
  return request("/execute", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function sendRobotCommand(sequence: string): Promise<{
  ok: boolean;
  chars_sent: number;
  sequence: string;
  log: ExecuteCommandLog[];
  error: string | null;
}> {
  return request("/robot/send", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sequence }),
  });
}

// --- Robot mode (sim / live BT) --------------------------------------------

export async function getRobotMode(): Promise<{ sim: boolean }> {
  return request("/robot/mode");
}

export async function setRobotMode(sim: boolean): Promise<{ sim: boolean }> {
  return request("/robot/mode", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ sim }),
  });
}

// --- Closed-loop /execute/stream (Server-Sent Events) ----------------------
//
// Native EventSource is GET-only and we need POST + JSON body, so we drive
// the stream with fetch + a ReadableStream parser. Yields parsed
// `{event, data}` records for the React component to consume via for-await.

export type StreamEvent =
  | { event: "step"; data: StepEventData }
  | { event: "ack"; data: AckEventData }
  | { event: "done"; data: DoneEventData }
  | { event: "aborted"; data: TerminalEventData }
  | { event: "stuck"; data: StuckEventData }
  | { event: "step_budget_exceeded"; data: BudgetEventData }
  | { event: "error"; data: ErrorEventData };

export type StepEventData = {
  step_idx: number;
  pose: { x_m: number; y_m: number; heading_deg: number } | null;
  next_cmd: string | null;
  sequence_so_far: string;
  frame_b64: string;
};

export type AckEventData = {
  step_idx: number;
  cmd: string;
  reply: string;
  elapsed_ms: number;
  ok: boolean;
  error?: string;
};

export type DoneEventData = { sequence: string; steps: number; message: string };
export type TerminalEventData = { sequence: string; steps: number };
export type StuckEventData = TerminalEventData & { pose: { x_m: number; y_m: number; heading_deg: number } };
export type BudgetEventData = TerminalEventData & { max_steps: number };
export type ErrorEventData = {
  error: string;
  message?: string;
  sequence?: string;
  steps?: number;
  frame_b64?: string;
};

export async function* executeStream(body: {
  task: "navigate" | "pick_place";
  source_shelf_id?: string;
  destination_shelf_id: string;
  port?: string;
  baud?: number;
  signal?: AbortSignal;
}): AsyncGenerator<StreamEvent> {
  const { signal, ...payload } = body;
  const res = await fetch(`${API_BASE}/execute/stream`, {
    method: "POST",
    headers: { "content-type": "application/json", "accept": "text/event-stream" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw new Error(JSON.stringify(detail));
  }
  if (!res.body) throw new Error("No response body for SSE stream");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // SSE frames are separated by blank lines. Within a frame, lines starting
  // with "event:" / "data:" carry the payload. We accumulate bytes, split on
  // blank-line boundaries, and parse each complete frame.
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let eventName = "message";
      let dataText = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataText += line.slice(5).trim();
      }
      if (!dataText) continue;
      try {
        const data = JSON.parse(dataText);
        yield { event: eventName, data } as StreamEvent;
      } catch {
        // Malformed frame -> skip rather than abort the whole stream.
      }
    }
  }
}

export async function abortExecute(): Promise<{ ok: boolean; running: boolean }> {
  return request("/execute/abort", { method: "POST" });
}

// --- Canned (no-vision) pick-place -----------------------------------------

export type CannedExecuteStep = {
  label: string;
  ok: boolean;
  elapsed_ms: number;
  reply: string;
  error?: string | null;
};

export type CannedExecuteResponse = {
  ok: boolean;
  from_shelf: string;
  to_shelf: string;
  steps: CannedExecuteStep[];
  error?: string | null;
};

export async function executeCanned(body: {
  from_shelf: string;
  to_shelf: string;
}): Promise<CannedExecuteResponse> {
  return request("/execute/canned", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

// --- Inventory: orders, stock, auto-replenish ------------------------------

export type OrderStatus = "pending" | "running" | "done" | "failed" | "cancelled";

export type Order = {
  id: number;
  sku_id: string;
  source_shelf_id: string;
  destination_shelf_id: string;
  qty: number;
  status: OrderStatus;
  created_at: number;
  started_at: number | null;
  finished_at: number | null;
  error: string | null;
  reason: string;
};

export type ShelfInventory = {
  shelf_id: string;
  sku_id: string | null;
  inventory_count: number;
  capacity: number;
};

export type SkuTotal = {
  sku_id: string;
  total: number;
  capacity: number;
  shelves: string[];
};

export type ReplenishProposal = {
  sku_id: string;
  source_shelf_id: string;
  destination_shelf_id: string;
  qty: number;
  reason: string;
};

export async function listOrders(status?: OrderStatus): Promise<{ orders: Order[] }> {
  const q = status ? `?status=${status}` : "";
  return request(`/orders${q}`);
}

export async function createOrder(body: {
  sku_id: string;
  source_shelf_id: string;
  destination_shelf_id: string;
  qty?: number;
  reason?: string;
}): Promise<Order> {
  return request("/orders", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function cancelOrder(id: number): Promise<Order> {
  return request(`/orders/${id}`, { method: "DELETE" });
}

export async function getInventory(): Promise<{ shelves: ShelfInventory[]; skus: SkuTotal[] }> {
  return request("/inventory");
}

export async function previewReplenish(thresholdFraction?: number): Promise<{ proposals: ReplenishProposal[] }> {
  return request("/replenish/preview", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ threshold_fraction: thresholdFraction ?? null }),
  });
}

export async function runReplenish(thresholdFraction?: number): Promise<{ enqueued: Order[]; skipped: ReplenishProposal[] }> {
  return request("/replenish/run", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ threshold_fraction: thresholdFraction ?? null }),
  });
}

export async function updateShelfInventory(
  shelfId: string,
  body: { sku_id?: string | null; inventory_count: number },
): Promise<ShelfInventory> {
  return request(`/inventory/shelf/${encodeURIComponent(shelfId)}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export type RunNextOrderResult = {
  ok: boolean;
  order: Order | null;
  executed: CannedExecuteResponse | null;
  message: string;
};

export async function runNextOrder(): Promise<RunNextOrderResult> {
  return request("/orders/run-next", { method: "POST" });
}

// --- Inventory-RL advisor (separate service on :8000) ----------------------

const RL_API_BASE = "http://127.0.0.1:8000";

export type RLPrediction = {
  action: number;
  order_quantity: number;
  reasoning: string;
  inventory_status: string;
  demand_forecast: string;
  formatted_log: string;
};

export type RLStatus = {
  status: string;
  model_loaded: boolean;
  requests_served: number;
  total_units_ordered: number;
  last_5_orders: number[];
};

export async function rlStatus(): Promise<RLStatus> {
  const res = await fetch(`${RL_API_BASE}/`);
  if (!res.ok) throw new Error(`rl_status ${res.status}`);
  return res.json();
}

export async function rlPredict(body: {
  inventory: number;
  day_index: number;
  day_of_week: number;
  previous_demand?: number | null;
  previous_sold?: number | null;
}): Promise<RLPrediction> {
  const res = await fetch(`${RL_API_BASE}/predict`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw new Error(JSON.stringify(detail));
  }
  return res.json();
}

export async function rlReset(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${RL_API_BASE}/reset`, { method: "POST" });
  if (!res.ok) throw new Error(`rl_reset ${res.status}`);
  return res.json();
}

// --- RL forecasting / multi-episode simulation -----------------------------

export type RLPolicy = "random" | "eoq" | "rl";

export type RLEpisodeDay = {
  day: number;
  day_of_week: string;
  inventory_start: number;
  order_qty: number;
  demand: number;
  sold: number;
  unmet_demand: number;
  inventory_end: number;
  reward: number;
};

export type RLEpisodeStat = {
  episode: number;
  total_reward: number;
  stockout_days: number;
  overstock_days: number;
  service_level: number;
  avg_inventory: number;
};

export type RLAggregate = {
  avg_total_reward: number;
  avg_stockout_days: number;
  avg_overstock_days: number;
  avg_service_level: number;
  avg_inventory: number;
};

export type RLSimulateResult = {
  policy: RLPolicy;
  policy_label: string;
  episodes_run: number;
  aggregate: RLAggregate;
  per_episode: RLEpisodeStat[];
  last_episode_days: RLEpisodeDay[];
  used_model: boolean;
  notes: string;
  heatmap: number[][];
};

export type RLPolicyComparisonRow = {
  policy: RLPolicy;
  policy_label: string;
  used_model: boolean;
  aggregate: RLAggregate;
  per_episode_rewards: number[];
  notes: string;
};

export type RLCompareResult = {
  rows: RLPolicyComparisonRow[];
  episodes: number;
  seed: number | null;
};

export type RLSimulateRequest = {
  policy: RLPolicy;
  episodes: number;
  seed?: number | null;
  initial_inventory: number;
  max_capacity: number;
  trend_strength: number;
  eoq_avg_demand?: number;
  eoq_reorder_point?: number;
};

export async function rlSimulate(body: RLSimulateRequest): Promise<RLSimulateResult> {
  const res = await fetch(`${RL_API_BASE}/simulate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw new Error(JSON.stringify(detail));
  }
  return res.json();
}

export type RLCompareRequest = {
  episodes: number;
  seed?: number | null;
  initial_inventory: number;
  max_capacity: number;
  trend_strength: number;
  eoq_avg_demand?: number;
  eoq_reorder_point?: number;
};

export async function rlCompare(body: RLCompareRequest): Promise<RLCompareResult> {
  const res = await fetch(`${RL_API_BASE}/compare`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: unknown;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw new Error(JSON.stringify(detail));
  }
  return res.json();
}

// --- Movement plans (operator-built sequences run from the UI) -------------

export type MovementStepType =
  | "drive_forward" | "drive_backward" | "turn_left" | "turn_right"
  | "lift_to" | "lift_up_for" | "lift_down_for"
  | "slider_extend" | "slider_retract"
  | "gripper_open" | "gripper_close"
  | "wait";

export type MovementStep = {
  type: MovementStepType;
  duration_ms: number;
  target_cm: number;
  note: string;
};

export type MovementPlan = {
  name: string;
  steps: MovementStep[];
  note: string;
};

export type MovementPlanRunResult = {
  ok: boolean;
  plan_name: string;
  steps: CannedExecuteStep[];
  error: string | null;
  sim: boolean;
};

export async function listPlans(): Promise<{ plans: MovementPlan[] }> {
  return request("/plans");
}

export async function savePlan(name: string, plan: MovementPlan): Promise<MovementPlan> {
  return request(`/plans/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(plan),
  });
}

export async function deletePlan(name: string): Promise<{ ok: boolean }> {
  return request(`/plans/${encodeURIComponent(name)}`, { method: "DELETE" });
}

export async function runPlan(name: string): Promise<MovementPlanRunResult> {
  return request(`/plans/${encodeURIComponent(name)}/run`, { method: "POST" });
}
