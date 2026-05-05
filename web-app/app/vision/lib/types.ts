export type ApproachPoint = {
  x_m: number;
  y_m: number;
  heading_deg: number;
};

export type Shelf = {
  id: string;
  x_m: number;
  y_m: number;
  width_m: number;
  length_m: number;
  rotation_deg: number;
  approach_point: ApproachPoint;
  sku_id?: string | null;
  inventory_count?: number;
  capacity?: number;
  // Lift target on the carriage's upward-facing ultrasonic. Smaller cm =
  // higher floor. Null/undefined for legacy single-floor shelves.
  floor_distance_cm?: number | null;
};

export type CalibrationStatus = {
  intrinsic: boolean;
  extrinsic: boolean;
};

export type RobotPose = {
  x_m: number;
  y_m: number;
  heading_deg: number;
  confidence: number;
};

export type Pose2D = {
  x_m: number;
  y_m: number;
  heading_deg: number;
};

export type Waypoint = {
  type: "turn" | "drive" | "grab" | "place" | "arrive";
  target_heading_deg?: number;
  distance_m?: number;
  from_pose?: Pose2D;
  to_pose?: Pose2D;
  shelf_id?: string;
};

export type PlanMetrics = {
  total_distance_m: number;
  estimated_time_s: number;
};

export type Settings = {
  workspace: { width_m: number; height_m: number; cell_size_m: number };
  robot: {
    footprint_m: [number, number];
    travel_height_m: number;
    markers: { front_color: string; back_color: string };
  };
  camera: { source: number | string; resolution: [number, number] };
  planner: { obstacle_inflation_m: number };
  robot_link?: { type: "wifi" | "sim"; host: string; port: number };
};

export type ApiError = { error: string; message?: string; details?: unknown };
