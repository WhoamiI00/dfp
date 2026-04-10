"use client";
import { useEffect, useState } from "react";
import {
  getCalibrationStatus, calibrateIntrinsic, calibrateExtrinsic, calibrateSynthetic,
} from "../lib/api";
import type { CalibrationStatus } from "../lib/types";
import ManualExtrinsicPanel from "./ManualExtrinsicPanel";
import ColorPickerPanel from "./ColorPickerPanel";

export default function CalibrationTab() {
  const [status, setStatus] = useState<CalibrationStatus | null>(null);
  const [message, setMessage] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try { setStatus(await getCalibrationStatus()); }
    catch (e) { setMessage(String(e)); }
  };
  useEffect(() => { refresh(); }, []);

  const handleIntrinsic = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await calibrateIntrinsic(Array.from(files));
      setMessage(`Intrinsic OK — error ${result.calibration_error_px.toFixed(2)} px, ${result.captured_images} images`);
      await refresh();
    } catch (e) {
      setMessage(`Intrinsic failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const handleExtrinsic = async () => {
    setBusy(true);
    setMessage("");
    try {
      const result = await calibrateExtrinsic();
      setMessage(`Extrinsic OK — error ${result.calibration_error_px.toFixed(2)} px`);
      await refresh();
    } catch (e) {
      setMessage(`Extrinsic failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  const handleSynthetic = async () => {
    setBusy(true);
    setMessage("");
    try {
      const r = await calibrateSynthetic();
      setMessage(
        `Synthetic calibration injected — image ${r.image_size[0]}x${r.image_size[1]}, f=${r.focal_length_px.toFixed(0)}px, camera height ${r.synthetic_camera_height_m}m`,
      );
      await refresh();
    } catch (e) {
      setMessage(`Synthetic calibration failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-4">
        <div className="p-4 border border-white/10 rounded">
          <div className="text-sm text-white/60">Intrinsic</div>
          <div className={status?.intrinsic ? "text-green-400" : "text-red-400"}>
            {status?.intrinsic ? "Calibrated" : "Missing"}
          </div>
        </div>
        <div className="p-4 border border-white/10 rounded">
          <div className="text-sm text-white/60">Extrinsic</div>
          <div className={status?.extrinsic ? "text-green-400" : "text-red-400"}>
            {status?.extrinsic ? "Calibrated" : "Missing"}
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <label className="block font-semibold">Intrinsic calibration</label>
        <p className="text-sm text-white/60">Upload 8 or more photos of a printed 9x6 chessboard.</p>
        <input
          type="file"
          multiple
          accept="image/*"
          disabled={busy}
          onChange={(e) => handleIntrinsic(e.target.files)}
          className="block"
          title="Chessboard images"
          aria-label="Chessboard images"
        />
      </div>

      <div className="space-y-2">
        <label className="block font-semibold">Extrinsic calibration</label>
        <p className="text-sm text-white/60">
          Place 4 ArUco markers (DICT_4X4_50, IDs 0-3) at workspace corners, then click:
        </p>
        <button
          type="button"
          disabled={busy || !status?.intrinsic}
          onClick={handleExtrinsic}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          Run extrinsic calibration
        </button>
      </div>

      <ManualExtrinsicPanel onCalibrated={refresh} />

      <ColorPickerPanel />

      <div className="space-y-2 rounded border border-amber-500/30 bg-amber-500/5 p-4">
        <label className="block font-semibold text-amber-300">
          Synthetic calibration (dev only)
        </label>
        <p className="text-sm text-white/70">
          Injects intrinsics and extrinsics for a top-down overhead camera
          using the current frame&apos;s dimensions. Use this with an
          uploaded top-down test image to skip real calibration. Not
          accurate for corner-mounted cameras or real hardware.
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={handleSynthetic}
          className="px-4 py-2 bg-amber-600 text-white rounded disabled:opacity-50"
        >
          Inject synthetic calibration
        </button>
      </div>

      {message && (
        <div className="p-3 bg-white/5 border border-white/10 rounded text-sm">{message}</div>
      )}
    </div>
  );
}
