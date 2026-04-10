"use client";
import { useEffect, useState } from "react";
import {
  getCalibrationStatus, calibrateIntrinsic, calibrateExtrinsic,
} from "../lib/api";
import type { CalibrationStatus } from "../lib/types";

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
        />
      </div>

      <div className="space-y-2">
        <label className="block font-semibold">Extrinsic calibration</label>
        <p className="text-sm text-white/60">
          Place 4 ArUco markers (DICT_4X4_50, IDs 0-3) at workspace corners, then click:
        </p>
        <button
          disabled={busy || !status?.intrinsic}
          onClick={handleExtrinsic}
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          Run extrinsic calibration
        </button>
      </div>

      {message && (
        <div className="p-3 bg-white/5 border border-white/10 rounded text-sm">{message}</div>
      )}
    </div>
  );
}
