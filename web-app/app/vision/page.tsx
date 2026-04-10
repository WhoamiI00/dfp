"use client";
import { useState } from "react";
import CalibrationTab from "./components/CalibrationTab";
import LayoutEditorTab from "./components/LayoutEditorTab";
import PlanRunTab from "./components/PlanRunTab";
import CameraSourceBar from "./components/CameraSourceBar";

type Tab = "calibration" | "layout" | "plan";

export default function VisionPage() {
  const [tab, setTab] = useState<Tab>("calibration");
  return (
    <div className="min-h-screen bg-black text-white p-6">
      <h1 className="text-2xl font-bold mb-4">Vision Control</h1>
      <CameraSourceBar />
      <nav className="flex gap-2 mb-6 border-b border-white/10">
        {(["calibration", "layout", "plan"] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 ${tab === t ? "border-b-2 border-blue-400 text-blue-400" : "text-white/60"}`}
          >
            {t === "calibration" ? "Calibration" : t === "layout" ? "Layout Editor" : "Plan & Run"}
          </button>
        ))}
      </nav>
      {tab === "calibration" && <CalibrationTab />}
      {tab === "layout" && <LayoutEditorTab />}
      {tab === "plan" && <PlanRunTab />}
    </div>
  );
}
