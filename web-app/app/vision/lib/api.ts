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

export async function capture(): Promise<{ image_base64: string }> {
  return request("/capture");
}

export async function detect(): Promise<{ robot_pose: RobotPose | null; reason: string | null; annotated_image_base64: string }> {
  return request("/detect", { method: "POST" });
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
