"use client";
import { useEffect, useRef, useState } from "react";
import {
  getCameraMode, setCameraImage, clearCameraImage, type CameraMode,
} from "../lib/api";

export default function CameraSourceBar() {
  const [mode, setMode] = useState<CameraMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewName, setPreviewName] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCameraMode().then(r => setMode(r.mode)).catch(e => setError(String(e)));
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    setError(null);
    try {
      const r = await setCameraImage(f);
      setMode(r.mode);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(URL.createObjectURL(f));
      setPreviewName(f.name);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function onClear() {
    setBusy(true);
    setError(null);
    try {
      const r = await clearCameraImage();
      setMode(r.mode);
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
      setPreviewName(null);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mb-4 rounded border border-white/10 bg-white/5 px-4 py-3 text-sm">
      <div className="flex items-center gap-3">
        <span className="font-semibold">Camera source:</span>
        <span
          className={
            mode === "test_image"
              ? "rounded bg-amber-500/20 px-2 py-0.5 text-amber-300"
              : "rounded bg-green-500/20 px-2 py-0.5 text-green-300"
          }
        >
          {mode === null ? "…" : mode === "test_image" ? "Test image" : "Live camera"}
        </span>
        <label className="ml-2 cursor-pointer rounded bg-blue-600 px-3 py-1 hover:bg-blue-500">
          Upload test image
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={onUpload}
            disabled={busy}
          />
        </label>
        {mode === "test_image" && (
          <button
            type="button"
            onClick={onClear}
            disabled={busy}
            className="rounded bg-white/10 px-3 py-1 hover:bg-white/20"
          >
            Use live camera
          </button>
        )}
        {error && <span className="text-red-400">{error}</span>}
      </div>
      {previewUrl && (
        <div className="mt-3 flex items-start gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Uploaded test image"
            className="max-h-40 rounded border border-white/10"
          />
          <div className="text-xs text-white/60">
            <div className="font-mono">{previewName}</div>
            <div className="mt-1">
              This image is now the current camera frame. Go to the
              <span className="text-blue-300"> Plan &amp; Run </span>
              tab and click <span className="text-blue-300">Capture</span> or
              <span className="text-blue-300"> Detect</span> to run the vision
              pipeline on it.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
