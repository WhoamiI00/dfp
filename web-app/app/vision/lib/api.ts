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
