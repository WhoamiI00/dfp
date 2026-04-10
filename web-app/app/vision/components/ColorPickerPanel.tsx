"use client";
import { useEffect, useRef, useState } from "react";
import {
  capture,
  sampleHsv,
  listCustomHsvRanges,
  upsertCustomHsvRange,
  deleteCustomHsvRange,
  type HsvBand,
  type HsvSampleResult,
  type CustomHsvEntry,
} from "../lib/api";

function hsvToCssColor(h: number, s: number, v: number): string {
  // OpenCV HSV uses H in [0, 179], S/V in [0, 255]. Convert to CSS hsl().
  const hDeg = (h / 179) * 360;
  const sPct = (s / 255) * 100;
  const lPct = ((v / 255) * (255 - s / 2)) / 255 * 100;
  return `hsl(${hDeg.toFixed(0)} ${sPct.toFixed(0)}% ${Math.min(95, Math.max(5, lPct)).toFixed(0)}%)`;
}

function BandSwatch({ band }: { band: HsvBand }) {
  const h = (band.h_min + band.h_max) / 2;
  const s = (band.s_min + band.s_max) / 2;
  const v = (band.v_min + band.v_max) / 2;
  return (
    <div
      title={`H ${band.h_min}-${band.h_max}  S ${band.s_min}-${band.s_max}  V ${band.v_min}-${band.v_max}`}
      className="inline-block w-6 h-6 rounded border border-white/20"
      style={{ backgroundColor: hsvToCssColor(h, s, v) }}
    />
  );
}

export default function ColorPickerPanel() {
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ w: number; h: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [sample, setSample] = useState<HsvSampleResult | null>(null);
  const [clickPx, setClickPx] = useState<[number, number] | null>(null);
  const [colorName, setColorName] = useState("");
  const [saved, setSaved] = useState<CustomHsvEntry[]>([]);
  const imgRef = useRef<HTMLImageElement>(null);

  const refreshSaved = async () => {
    try {
      const r = await listCustomHsvRanges();
      setSaved(r.entries);
    } catch (e) {
      setMessage(`Failed to load saved colors: ${e}`);
    }
  };

  useEffect(() => { refreshSaved(); }, []);

  useEffect(() => {
    if (!imageB64) return;
    const img = new Image();
    img.onload = () => setImageSize({ w: img.naturalWidth, h: img.naturalHeight });
    img.src = `data:image/png;base64,${imageB64}`;
  }, [imageB64]);

  const handleCapture = async () => {
    setBusy(true);
    setMessage(null);
    setSample(null);
    setClickPx(null);
    try {
      const r = await capture();
      setImageB64(r.image_base64);
    } catch (e) {
      setMessage(String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleClick = async (e: React.MouseEvent<HTMLImageElement>) => {
    if (!imgRef.current || !imageSize) return;
    const rect = imgRef.current.getBoundingClientRect();
    const scaleX = imageSize.w / rect.width;
    const scaleY = imageSize.h / rect.height;
    const u = Math.round((e.clientX - rect.left) * scaleX);
    const v = Math.round((e.clientY - rect.top) * scaleY);
    setClickPx([u, v]);
    setBusy(true);
    setMessage(null);
    try {
      const result = await sampleHsv(u, v, 7);
      setSample(result);
    } catch (err) {
      setMessage(`Sample failed: ${err}`);
    } finally {
      setBusy(false);
    }
  };

  const handleSave = async () => {
    if (!sample || !colorName.trim()) return;
    setBusy(true);
    try {
      await upsertCustomHsvRange(colorName.trim().toLowerCase(), sample.bands);
      setMessage(`Saved "${colorName.trim().toLowerCase()}". Use this name in settings.yaml or the auto-detect panel.`);
      setColorName("");
      await refreshSaved();
    } catch (err) {
      setMessage(`Save failed: ${err}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (name: string) => {
    setBusy(true);
    try {
      await deleteCustomHsvRange(name);
      await refreshSaved();
      setMessage(`Removed "${name}".`);
    } catch (err) {
      setMessage(`Delete failed: ${err}`);
    } finally {
      setBusy(false);
    }
  };

  const centerColor = sample
    ? hsvToCssColor(sample.median_h, sample.median_s, sample.median_v)
    : null;

  return (
    <div className="space-y-2 rounded border border-fuchsia-500/30 bg-fuchsia-500/5 p-4">
      <label className="block font-semibold text-fuchsia-300">
        Color picker (sample marker colour from image)
      </label>
      <p className="text-sm text-white/70">
        Capture the current frame, click a pixel on the marker you want to
        track, give it a name, and save. The saved colour becomes available
        anywhere a colour name is used (settings.yaml robot markers, the
        shelves auto-detect panel). Lighting-adaptive — just re-sample if
        the scene changes.
      </p>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleCapture}
          disabled={busy}
          className="px-3 py-1 bg-fuchsia-600 text-white rounded disabled:opacity-50"
        >
          Capture frame
        </button>
      </div>

      {imageB64 && (
        <div className="flex gap-4">
          <div className="relative inline-block max-w-lg">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={imgRef}
              src={`data:image/png;base64,${imageB64}`}
              alt="click to sample"
              onClick={handleClick}
              className="max-w-full cursor-crosshair border border-white/20"
            />
            {imageSize && clickPx && imgRef.current && (() => {
              const rect = imgRef.current.getBoundingClientRect();
              const sx = rect.width / imageSize.w;
              const sy = rect.height / imageSize.h;
              return (
                <div
                  className="absolute w-4 h-4 rounded-full border-2 border-fuchsia-400 pointer-events-none"
                  style={{
                    left: clickPx[0] * sx - 8,
                    top: clickPx[1] * sy - 8,
                  }}
                />
              );
            })()}
          </div>

          {sample && (
            <div className="text-sm space-y-2 min-w-[16rem]">
              <div className="flex items-center gap-2">
                <div
                  className="w-10 h-10 rounded border border-white/20"
                  style={{ backgroundColor: centerColor ?? "transparent" }}
                />
                <div className="text-xs text-white/70">
                  <div>H {sample.median_h} S {sample.median_s} V {sample.median_v}</div>
                  <div>{sample.bands.length} band{sample.bands.length === 1 ? "" : "s"}</div>
                </div>
              </div>
              <div className="flex gap-1">
                {sample.bands.map((b, i) => <BandSwatch key={i} band={b} />)}
              </div>
              <div className="pt-1">
                <input
                  type="text"
                  placeholder="name (e.g. my_pink)"
                  value={colorName}
                  onChange={e => setColorName(e.target.value)}
                  className="w-full bg-black border border-white/20 px-2 py-1"
                  disabled={busy}
                />
              </div>
              <button
                type="button"
                onClick={handleSave}
                disabled={busy || !colorName.trim()}
                className="w-full px-3 py-1 bg-green-600 text-white rounded disabled:opacity-50"
              >
                Save colour
              </button>
            </div>
          )}
        </div>
      )}

      {saved.length > 0 && (
        <div className="pt-2 border-t border-white/10">
          <div className="text-xs text-white/70 mb-1">Saved custom colours</div>
          <ul className="space-y-1">
            {saved.map(entry => (
              <li key={entry.name} className="flex items-center gap-2 text-sm">
                <span className="flex gap-1">
                  {entry.bands.map((b, i) => <BandSwatch key={i} band={b} />)}
                </span>
                <span className="flex-1 font-mono">{entry.name}</span>
                <button
                  type="button"
                  onClick={() => handleDelete(entry.name)}
                  disabled={busy}
                  className="px-2 py-0.5 text-xs bg-red-600/70 rounded disabled:opacity-50"
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
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
