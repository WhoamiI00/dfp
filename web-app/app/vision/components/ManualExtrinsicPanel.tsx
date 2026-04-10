"use client";
import { useEffect, useRef, useState } from "react";
import { capture, calibrateExtrinsicManual } from "../lib/api";

const CORNER_LABELS = [
  "1: bottom-left (0, 0)",
  "2: bottom-right (W, 0)",
  "3: top-right (W, H)",
  "4: top-left (0, H)",
];

type Props = {
  onCalibrated: () => void;
};

export default function ManualExtrinsicPanel({ onCalibrated }: Props) {
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ w: number; h: number } | null>(null);
  const [corners, setCorners] = useState<[number, number][]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const handleCapture = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const r = await capture();
      setImageB64(r.image_base64);
      setCorners([]);
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!imageB64) return;
    const img = new Image();
    img.onload = () => setImageSize({ w: img.naturalWidth, h: img.naturalHeight });
    img.src = `data:image/png;base64,${imageB64}`;
  }, [imageB64]);

  const handleClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!imgRef.current || !imageSize) return;
    if (corners.length >= 4) return;
    const rect = imgRef.current.getBoundingClientRect();
    const scaleX = imageSize.w / rect.width;
    const scaleY = imageSize.h / rect.height;
    const u = (e.clientX - rect.left) * scaleX;
    const v = (e.clientY - rect.top) * scaleY;
    setCorners([...corners, [u, v]]);
  };

  const handleReset = () => {
    setCorners([]);
    setMessage(null);
  };

  const handleCalibrate = async () => {
    if (corners.length !== 4) return;
    setBusy(true);
    setMessage(null);
    try {
      const r = await calibrateExtrinsicManual(corners);
      setMessage(`Calibrated — reprojection error ${r.calibration_error_px.toFixed(2)} px`);
      onCalibrated();
    } catch (e) {
      setMessage(`Calibration failed: ${e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-2 rounded border border-blue-500/30 bg-blue-500/5 p-4">
      <label className="block font-semibold text-blue-300">
        Click-to-calibrate extrinsics
      </label>
      <p className="text-sm text-white/70">
        Capture the current frame, then click the four workspace corners in
        order: bottom-left, bottom-right, top-right, top-left. Backend runs
        solvePnP to compute real extrinsics from your clicks. Requires
        intrinsics to already be set (real or synthetic).
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleCapture}
          disabled={busy}
          className="px-3 py-1 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          Capture frame
        </button>
        {imageB64 && (
          <>
            <button
              type="button"
              onClick={handleReset}
              disabled={busy || corners.length === 0}
              className="px-3 py-1 bg-white/10 rounded disabled:opacity-50"
            >
              Reset clicks
            </button>
            <button
              type="button"
              onClick={handleCalibrate}
              disabled={busy || corners.length !== 4}
              className="px-3 py-1 bg-green-600 text-white rounded disabled:opacity-50"
            >
              Calibrate
            </button>
          </>
        )}
      </div>

      {imageB64 && (
        <div className="relative inline-block">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={imgRef}
            src={`data:image/png;base64,${imageB64}`}
            alt="click corners"
            onClick={handleClick}
            className="max-w-full cursor-crosshair border border-white/20"
          />
          {imageSize && corners.map(([u, v], i) => {
            const rect = imgRef.current?.getBoundingClientRect();
            if (!rect) return null;
            const scaleX = rect.width / imageSize.w;
            const scaleY = rect.height / imageSize.h;
            return (
              <div
                key={i}
                className="absolute flex items-center justify-center text-xs font-bold text-white bg-red-600 rounded-full pointer-events-none"
                style={{
                  width: 22,
                  height: 22,
                  left: u * scaleX - 11,
                  top: v * scaleY - 11,
                }}
              >
                {i + 1}
              </div>
            );
          })}
        </div>
      )}

      {imageB64 && (
        <div className="text-xs text-white/60">
          Clicks: {corners.length}/4.
          {corners.length < 4 && (
            <span className="ml-1 text-blue-300">
              Next: {CORNER_LABELS[corners.length]}
            </span>
          )}
        </div>
      )}

      {message && (
        <div className="p-2 bg-white/5 border border-white/10 rounded text-sm">
          {message}
        </div>
      )}
    </div>
  );
}
