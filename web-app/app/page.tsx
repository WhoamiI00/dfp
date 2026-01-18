"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { Reveal } from "@/components/Reveal";
import { StompHeader } from "@/components/StompHeader";
import { FloatingBlocks } from "@/components/FloatingBlocks";

// Navigation Component
function Navigation() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 px-6 py-4 transition-all duration-500 ${scrolled ? "bg-black/80 backdrop-blur-xl border-b border-white/5" : "bg-transparent"}`}>
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <a href="#" className="text-xl font-black tracking-tighter text-white select-none">IVEN-TRON</a>
        <div className="hidden md:flex gap-8 text-[10px] tracking-[0.2em] font-medium uppercase text-white/50">
          <a href="#methodology" className="hover:text-white transition-colors">Methodology</a>
          <a href="#overview" className="hover:text-white transition-colors">Overview</a>
          <a href="#survey" className="hover:text-white transition-colors">Survey</a>
          <a href="#engineering" className="hover:text-white transition-colors">Engineering</a>
          <a href="#bom" className="hover:text-white transition-colors">BOM</a>
          <a href="#team" className="hover:text-white transition-colors">Team</a>
        </div>
      </div>
    </nav>
  );
}

// Methodology Section
function MethodologySection() {
  const steps = [
    { name: "EMPATHIZE", icon: "/methodology-empathize.png" },
    { name: "DEFINE", icon: "/methodology-define.png" },
    { name: "IDEATE", icon: "/methodology-ideate.png" },
    { name: "PROTOTYPE", icon: "/methodology-prototype.png" },
    { name: "TEST", icon: "/methodology-test.png" },
  ];

  return (
    <section id="methodology" className="h-full py-12 px-4 relative flex flex-col justify-center">
      <div>
        <h2 className="text-4xl md:text-6xl text-center mb-16 font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/20 opacity-90">METHODOLOGY</h2>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          {steps.map((step, i) => (
            <div key={i} className="flex items-center group">
              <div className="flex flex-col items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-neutral-900 border border-white/10 flex items-center justify-center group-hover:border-white/50 group-hover:scale-110 transition-all duration-500 shadow-[0_0_30px_rgba(255,255,255,0.05)]">
                  <img src={step.icon} alt={step.name} className="w-6 h-6 object-contain brightness-0 invert opacity-100 group-hover:scale-110 transition-transform" />
                </div>
                <span className="text-[10px] text-white/60 tracking-[0.2em] font-mono group-hover:text-white transition-colors">{step.name}</span>
              </div>
              {i < steps.length - 1 && (
                <div className="hidden md:flex items-center mx-2 opacity-30">
                  <div className="w-4 h-[1px] bg-gradient-to-r from-transparent via-white to-transparent" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// Project Overview Section
function ProjectOverviewSection() {
  return (
    <section id="overview" className="h-full py-12 px-4 relative overflow-hidden flex flex-col justify-center">
      <div className="absolute inset-0 bg-neutral-900/20" />
      <div className="relative z-10 w-full">
        <div className="border border-white/10 bg-black/40 backdrop-blur-sm p-8 rounded-2xl relative h-full flex flex-col justify-center">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-[1px] bg-gradient-to-r from-transparent via-white/50 to-transparent" />
          <h2 className="text-3xl md:text-5xl text-center mb-8 font-black tracking-tighter text-white">PROJECT OVERVIEW</h2>
          <p className="text-sm md:text-base text-white/70 text-center leading-relaxed font-light">
            The project focuses on designing and developing an IoT-enabled smart warehouse automation system
            that autonomously handles, stores, and manages finished products without human intervention. To enhance
            operational efficiency, a ML model predicts daily production requirements based on demand patterns and
            stock levels.
          </p>
        </div>
      </div>
    </section>
  );
}

// Video Display Section - Single Video & Clean Circuit
function VideoSection() {
  return (
    <section className="py-12 px-4">
      <div className="max-w-7xl mx-auto space-y-12">

        {/* Top: Circuit Diagram (Framed) */}
        <div className="flex flex-col items-center">
          <h3 className="text-white text-center mb-8 font-black tracking-widest text-xl uppercase">Circuit Diagram</h3>
          <div className="relative group p-4 bg-neutral-900/50 border border-white/10 rounded-2xl shadow-2xl shadow-blue-900/20 backdrop-blur-sm">
            <img
              src="/circuit_image.png"
              alt="IVEN-TRON Circuit Diagram"
              className="max-w-full h-auto max-h-[500px] object-contain transition-opacity hover:scale-105 duration-500"
            />
          </div>
        </div>

        {/* Bottom: Single Full-Width Video (Framed) */}
        <div className="w-full aspect-video bg-neutral-900 border border-white/10 rounded-2xl overflow-hidden relative group shadow-2xl shadow-blue-900/20">
          <video
            className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-700"
            autoPlay
            loop
            muted
            playsInline
            poster="/background-model.png"
          >
            <source src="/Simulation.mp4" type="video/mp4" />
            Your browser does not support the video tag.
          </video>

          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent pointer-events-none" />

          {/* Fallback/Overlay Text - Hidden on Mobile */}
          <div className="absolute inset-0 hidden md:flex items-center justify-center pointer-events-none">
            <p className="text-white font-black text-6xl uppercase tracking-tighter opacity-0 group-hover:opacity-100 transition-all duration-700 scale-150 group-hover:scale-100">
              System Simulation
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}


// Market Analysis Section
function MarketAnalysisSection() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl md:text-5xl text-white text-center mb-16 font-black tracking-tighter">MARKET ANALYSIS</h2>
        <div className="grid md:grid-cols-2 gap-12 mb-12">
          <div className="bg-neutral-900/50 border border-white/10 p-8 rounded-2xl">
            <h3 className="text-white/50 text-xs tracking-[0.2em] mb-6 uppercase">Current Landscape</h3>
            <ul className="text-base text-white/90 space-y-4 font-light">
              <li className="flex items-start gap-3">
                <span className="w-1.5 h-1.5 mt-2 rounded-full bg-blue-500" />
                Industry leaders (Amazon, AutoStore) use high-cost robotic systems.
              </li>
              <li className="flex items-start gap-3">
                <span className="w-1.5 h-1.5 mt-2 rounded-full bg-red-500" />
                Traditional SMEs rely on manual labor with poor accuracy.
              </li>
            </ul>
            <div className="flex gap-6 mt-8 opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
              <img src="/autostore.png" alt="AutoStore" className="h-6 object-contain" />
              <img src="/amazon.png" alt="Amazon" className="h-6 object-contain" />
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-gradient-to-br from-neutral-900 to-black border border-white/10 p-8 rounded-2xl group hover:border-white/30 transition-colors">
              <h3 className="text-2xl font-bold text-white mb-2 group-hover:text-blue-400 transition-colors">GAP</h3>
              <p className="text-white/60 font-light">Affordable automation + predictive intelligence.</p>
            </div>
            <div className="bg-gradient-to-br from-neutral-900 to-black border border-white/10 p-8 rounded-2xl group hover:border-white/30 transition-colors">
              <h3 className="text-2xl font-bold text-white mb-2 group-hover:text-green-400 transition-colors">OPPORTUNITY</h3>
              <p className="text-white/60 font-light">Low-cost robotic storage + RL-based demand prediction.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// Problem Statement Section
function ProblemStatementSection() {
  return (
    <section className="h-full bg-neutral-900/30 p-10 rounded-2xl border border-white/10 backdrop-blur-sm hover:bg-neutral-900/50 transition-colors duration-500">
      <h2 className="text-2xl text-white text-center mb-10 font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">PROBLEM STATEMENT</h2>
      <p className="text-base text-white/80 leading-relaxed text-center font-light">
        Current warehouse operations in small to medium-scale enterprises are inefficient due to a heavy
        reliance on manual labor, lack of real-time inventory visibility, and the inability to predict
        fluctuating market demand. This results in operational bottlenecks, frequent human errors, and
        financial losses caused by stock mismanagement.
      </p>
    </section>
  );
}

// Identified Problems Section
function IdentifiedProblemsSection() {
  return (
    <section className="h-full bg-neutral-900/30 p-10 rounded-2xl border border-white/10 backdrop-blur-sm hover:bg-neutral-900/50 transition-colors duration-500">
      <h2 className="text-2xl text-white text-center mb-10 font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">IDENTIFIED PROBLEMS</h2>
      <ul className="text-base text-white/80 space-y-4 max-w-xl mx-auto font-light">
        <li className="border-b border-white/5 pb-2 last:border-0">• Manual workflows create bottleneck, errors and safety risks.</li>
        <li className="border-b border-white/5 pb-2 last:border-0">• Paper logs cause visibility gaps and time lags.</li>
        <li className="border-b border-white/5 pb-2 last:border-0">• Storage decisions are not data-driven.</li>
        <li className="border-b border-white/5 pb-2 last:border-0">• SMEs lack integrated tracking + prediction tech.</li>
        <li className="border-b border-white/5 pb-2 last:border-0">• Industrial robots are expensive and infrastructure-heavy.</li>
      </ul>
    </section>
  );
}

// User Survey Section - Matching Figma Design
function UserSurveySection() {
  const [showAll, setShowAll] = useState(false);

  // Pie chart component with Percentage
  const PieChart = ({ data }: { data: { label: string; value: number; color: string }[] }) => {
    // Calculate total value
    const total = data.reduce((acc, curr) => acc + curr.value, 0);

    // Generate conic gradient string
    let currentAngle = 0;
    const gradientParts = data.map((item) => {
      const startAngle = currentAngle;
      const angle = (item.value / total) * 360;
      currentAngle += angle;
      return `${item.color} ${startAngle}deg ${currentAngle}deg`;
    });
    const gradient = `conic-gradient(${gradientParts.join(", ")})`;

    return (
      <div className="flex items-center gap-6">
        <div className="w-24 h-24 rounded-full flex-shrink-0 shadow-lg" style={{ background: gradient }} />
        <div className="flex flex-col gap-2">
          {data.map((item, i) => {
            const percentage = ((item.value / total) * 100).toFixed(1);
            return (
              <div key={i} className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full" style={{ background: item.color }} />
                <div className="flex flex-col">
                  <span className="text-[10px] uppercase tracking-wider text-white/60 leading-none">{item.label}</span>
                  <span className="text-[10px] font-bold text-white/90">{percentage}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Bar chart component
  const BarChart = ({ data }: { data: { label: string; value: number }[] }) => (
    <div className="w-full space-y-3">
      {data.map((d, i) => (
        <div key={i} className="flex items-center gap-3 group">
          <span className="text-[10px] uppercase tracking-wider text-white/50 w-32 text-right truncate group-hover:text-white transition-colors">{d.label}</span>
          <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
            <div className="h-full bg-white rounded-full group-hover:bg-blue-400 transition-all duration-1000 ease-out" style={{ width: `${d.value}%` }} />
          </div>
          <span className="text-[10px] text-white/40 font-mono w-8">{d.value}%</span>
        </div>
      ))}
    </div>
  );

  const surveyData = [
    {
      type: 'pie',
      question: '1. How do you currently pick items from shelves?',
      data: [
        { label: 'One at a time by hand', value: 31.3, color: '#3366CC' },
        { label: 'Manually with helper', value: 25, color: '#DC3912' },
        { label: 'Using forklifts', value: 25, color: '#FF9900' },
        { label: 'Using carts/trolleys', value: 12.5, color: '#109618' },
        { label: 'Other equipment', value: 6.2, color: '#990099' },
      ]
    },
    {
      type: 'pie',
      question: '2. Which shelf levels are most difficult to access?',
      data: [
        { label: 'Top shelves', value: 25, color: '#990099' },
        { label: 'Middle shelves', value: 37.5, color: '#109618' },
        { label: 'Bottom shelves', value: 25, color: '#3366CC' },
        { label: 'All equally difficult', value: 12.5, color: '#DC3912' },
      ]
    },
    {
      type: 'bar',
      question: '3. What challenges do you face while picking items?',
      data: [
        { label: 'Items placed too deep', value: 75 },
        { label: 'Items too heavy', value: 85 },
        { label: 'Risk of items falling', value: 90 },
        { label: 'Mislabeled locations', value: 70 },
        { label: 'Need to bend or stretch', value: 55 },
      ]
    },
    {
      type: 'pie',
      question: '4. How often do items get stuck/damaged?',
      data: [
        { label: 'Very often', value: 37.5, color: '#FF9900' },
        { label: 'Sometimes', value: 31.3, color: '#3366CC' },
        { label: 'Rarely', value: 20.1, color: '#109618' },
        { label: 'Never', value: 11.1, color: '#DC3912' },
      ]
    },
    {
      type: 'pie',
      question: '5. Digital inventory management system usage?',
      data: [
        { label: 'Yes, fully digital', value: 31.3, color: '#3366CC' },
        { label: 'Partly digital', value: 18.7, color: '#FF9900' },
        { label: 'Mostly manual', value: 25, color: '#109618' },
        { label: 'Completely manual', value: 25, color: '#DC3912' },
      ]
    },
    {
      type: 'pie',
      question: '6. How do you check item availability?',
      data: [
        { label: 'Mobile scanner', value: 37.5, color: '#FF9900' },
        { label: 'Computer terminal', value: 31.3, color: '#DC3912' },
        { label: 'Paper logs', value: 18.7, color: '#3366CC' },
        { label: 'Ask colleagues', value: 12.5, color: '#109618' },
      ]
    },
    {
      type: 'bar',
      question: '7. Inventory system problems?',
      data: [
        { label: 'Item location inaccurate', value: 50 },
        { label: 'Slow searching/updating', value: 95 },
        { label: 'Missing/inaccurate entries', value: 70 },
        { label: 'Manual data entry', value: 80 },
        { label: 'System is unreliable', value: 75 },
        { label: 'Too difficult', value: 60 },
      ]
    },
    {
      type: 'pie',
      question: '8. Frequency of out-of-stock?',
      data: [
        { label: 'Very often', value: 31.3, color: '#FF9900' },
        { label: 'Sometimes', value: 25, color: '#3366CC' },
        { label: 'Rarely', value: 25.6, color: '#109618' },
        { label: 'Never', value: 18, color: '#DC3912' },
      ]
    },
    {
      type: 'pie',
      question: '9. Prefer automation?',
      data: [
        { label: 'Yes, definitely', value: 75, color: '#3366CC' },
        { label: 'Maybe', value: 25, color: '#FF9900' },
      ]
    },
    {
      type: 'pie',
      question: '10. Support for automation?',
      data: [
        { label: 'Very likely', value: 56.3, color: '#3366CC' },
        { label: 'Likely', value: 18.7, color: '#109618' },
        { label: 'Unsure', value: 12.5, color: '#FF9900' },
        { label: 'Not likely', value: 12.5, color: '#DC3912' },
      ]
    }
  ];

  const visibleCount = showAll ? surveyData.length : 4;
  const visibleData = surveyData.slice(0, visibleCount);

  return (
    <section id="survey" className="py-24 px-4 bg-neutral-900/20 border-y border-white/5">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-4xl text-white text-center mb-16 font-black tracking-tighter">USER SURVEY</h2>

        <div className="grid md:grid-cols-2 gap-x-16 gap-y-12">
          {visibleData.map((item, index) => (
            <div key={index} className={`bg-black/40 p-6 rounded-xl border border-white/5 hover:border-white/10 transition-colors ${item.type === 'bar' ? 'span-2' : ''}`}>
              <h3 className="text-xs text-white mb-6 uppercase tracking-widest font-bold">{item.question}</h3>
              {item.type === 'pie' ? (
                <PieChart data={item.data as any} />
              ) : (
                <BarChart data={item.data as any} />
              )}
            </div>
          ))}
        </div>

        {!showAll && (
          <div className="text-center mt-12">
            <button
              onClick={() => setShowAll(true)}
              className="px-8 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs font-bold uppercase tracking-widest text-white transition-all duration-300"
            >
              Load More Graphs
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

// Technical Drawing Section
function TechnicalDrawingSection() {
  return (
    <section className="h-full bg-neutral-900/30 p-10 rounded-2xl border border-white/10 flex flex-col backdrop-blur-sm">
      <h2 className="text-2xl text-white text-center mb-10 font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">TECHNICAL DRAWING</h2>
      <div className="flex-1 flex items-center justify-center p-8 bg-black/40 rounded-xl border border-white/5">
        <img src="/technical-drawing.png" alt="IVEN-TRON Technical Drawing" className="max-w-full h-auto max-h-80 object-contain invert-[0.1]" />
      </div>
    </section>
  );
}

// Design Detailing Section
function DesignDetailingSection() {
  return (
    <section id="engineering" className="h-full bg-neutral-900/30 p-10 rounded-2xl border border-white/10 backdrop-blur-sm">
      <h2 className="text-2xl text-white text-center mb-10 font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">DESIGN DETAILING</h2>
      <div className="flex flex-col gap-10">
        <ul className="text-sm text-white/70 space-y-4 font-light">
          <li>• IVEN-TRON is a compact, modular autonomous warehouse robot integrating mechanical, electrical, and software subsystems.</li>
          <li>• A lightweight aluminum chassis with a gear-motor–driven vertical lift ensures rigid structure and safe height adjustment.</li>
          <li>• Box handling is performed using a servo-actuated U-shaped gripper supported by a sliding gap-bridge mechanism.</li>
          <li>• The robot uses a differential-drive base with high-torque DC motors, assisted by IR, ultrasonic, and limit sensors.</li>
          <li>• An Arduino Mega with L298N motor drivers enables real-time inventory updates through a finite-state control architecture.</li>
        </ul>
        <div className="flex justify-center relative">
          <div className="absolute inset-0 bg-blue-500/20 blur-[100px] pointer-events-none" />
          <Image src="/blender-model.png" alt="IVEN-TRON 3D Model" width={250} height={350} className="object-contain relative z-10" />
        </div>
      </div>
    </section>
  );
}

// Utility Section
function UtilitySection() {
  const utilities = [
    "Autonomous picking, lifting, and placing of items.",
    "Real-time sensor-based inventory visibility.",
    "RL-based demand prediction prevents shortages/excess.",
    "Raw material monitoring with automatic alerts.",
    "Low-cost tech suitable for SMEs.",
    "Higher safety and efficiency with reduced human error.",
  ];

  return (
    <section className="h-full bg-neutral-900/30 p-10 rounded-2xl border border-white/10 backdrop-blur-sm">
      <h2 className="text-2xl text-white text-center mb-10 font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">UTILITY</h2>
      <div className="grid grid-cols-2 gap-4">
        {utilities.map((util, i) => (
          <div key={i} className="p-4 text-center rounded-xl flex items-center justify-center bg-black/40 border border-white/5 hover:border-white/20 hover:scale-105 transition-all duration-300">
            <p className="text-xs text-white/80 font-mono tracking-tight">{util}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// Bill of Materials Section
function BOMSection() {
  const bom = [
    { item: "DC-100 RPM Motor", qty: 4, total: 1116 },
    { item: "L298N Motor Driver", qty: 1, total: 135 },
    { item: "HC-SR04 Ultrasonic", qty: 4, total: 228 },
    { item: "IR Avoidance Sensor", qty: 2, total: 70 },
    { item: "Arduino Mega 2560", qty: 1, total: 1467 },
    { item: "NEMA17 Stepper Motor", qty: 4, total: 2364 },
    { item: "ESP32-CAM", qty: 1, total: 429 },
    { item: "Servo Motor", qty: 2, total: 472 },
    { item: "HC-05 Bluetooth", qty: 1, total: 275 },
    { item: "Aluminum Profile", qty: 4, total: 232 },
    { item: "Stepper Driver", qty: 4, total: 272 },
    { item: "Miscellaneous", qty: 1, total: 1500 },
  ];

  const totalCost = bom.reduce((sum, item) => sum + item.total, 0);

  return (
    <section id="bom" className="py-24 px-4 bg-neutral-900/10 border-y border-white/5">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-4xl text-white text-center mb-16 font-black tracking-tighter">BILL OF MATERIALS</h2>
        <div className="overflow-hidden border border-white/10 rounded-2xl bg-black/20">
          <table className="w-full text-sm">
            <thead className="bg-white/5">
              <tr>
                <th className="text-left py-4 px-6 text-white/50 font-mono text-xs uppercase tracking-widest border-b border-white/10">Component</th>
                <th className="text-center py-4 px-6 text-white/50 font-mono text-xs uppercase tracking-widest border-b border-white/10">Qty</th>
                <th className="text-right py-4 px-6 text-white/50 font-mono text-xs uppercase tracking-widest border-b border-white/10">Cost (₹)</th>
              </tr>
            </thead>
            <tbody>
              {bom.map((item, i) => (
                <tr key={i} className="hover:bg-white/5 transition-colors">
                  <td className="py-3 px-6 text-white/80 border-b border-white/5 font-light">{item.item}</td>
                  <td className="py-3 px-6 text-white/80 text-center border-b border-white/5 font-mono text-xs opacity-50">{item.qty}</td>
                  <td className="py-3 px-6 text-white/80 text-right border-b border-white/5 font-mono text-xs">₹{item.total.toLocaleString()}</td>
                </tr>
              ))}
              <tr className="bg-white/5">
                <td colSpan={2} className="py-6 px-6 text-white font-bold text-lg">Total Cost</td>
                <td className="py-6 px-6 text-green-400 font-bold text-lg text-right font-mono">₹{totalCost.toLocaleString()}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

// Team Section - Matching Poster Design
function TeamSection() {
  const members = [
    { name: "Animesh", id: "23BDS013" },
    { name: "Aditya Kumar", id: "23BCS012" },
    { name: "Ankit Raj", id: "23BCS028" },
    { name: "Aniket Mishra", id: "23BEC016" },
    { name: "Jigyasa", id: "23BEC053" },
    { name: "Tarun Gupta", id: "23BSM062" },
  ];

  return (
    <section id="team" className="h-full bg-neutral-900/30 p-10 rounded-2xl border border-white/10 backdrop-blur-sm">
      <h2 className="text-2xl text-white text-center mb-10 font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-b from-white to-white/40">TEAM</h2>
      <div className="border border-white/10 rounded-xl overflow-hidden bg-black/20">
        {/* Course Info */}
        <div className="grid grid-cols-[120px_1fr] border-b border-white/10">
          <div className="py-3 px-4 text-[10px] text-white/40 uppercase tracking-widest bg-white/5 border-r border-white/10 flex items-center">Course</div>
          <div className="py-3 px-4 text-xs text-white font-mono">DS3001</div>
        </div>
        <div className="grid grid-cols-[120px_1fr] border-b border-white/10">
          <div className="py-3 px-4 text-[10px] text-white/40 uppercase tracking-widest bg-white/5 border-r border-white/10 flex items-center">Subject</div>
          <div className="py-3 px-4 text-xs text-white font-mono">Engineering Design & Fab.</div>
        </div>

        {/* Team Members */}
        <div className="grid grid-cols-[120px_1fr] border-b border-white/10">
          <div className="py-3 px-4 text-[10px] text-white/40 uppercase tracking-widest bg-white/5 border-r border-white/10 flex items-center">Members</div>
          <div className="py-4 px-4">
            <div className="grid grid-cols-2 gap-3">
              {members.map((m, i) => (
                <div key={i} className="text-xs text-white">
                  {m.name} <span className="text-white/30 font-mono ml-1">{m.id}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Institute */}
        <div className="py-4 px-4 text-center bg-white/5">
          <p className="text-[10px] text-white/40 uppercase tracking-[0.2em]">PDPM IIITDM Jabalpur</p>
        </div>
      </div>
    </section>
  );
}

// Footer
function Footer() {
  return (
    <footer className="py-12 px-4 border-t border-white/5 bg-black">
      <div className="flex flex-col items-center gap-4">
        <h3 className="text-2xl font-black text-white tracking-tighter">IVEN-TRON</h3>
        <p className="text-center text-xs text-white/30 tracking-widest">© 2026 DFP-38 | PDPM IIITDM JABALPUR</p>
      </div>
    </footer>
  );
}

// Main Page Component - Mixed Layout (Single & Two-Column)
export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white selection:bg-white selection:text-black" style={{ fontFamily: "'Inter', sans-serif" }}>
      <Navigation />
      <FloatingBlocks />

      {/* Awwwards Stomp Intro */}
      <StompHeader
        title="IVEN-TRON"
        subtitle="AUTONOMOUS SMART WAREHOUSE SYSTEM"
      />

      <main className="max-w-7xl mx-auto px-4 pt-8 pb-24 space-y-16 relative z-10">

        {/* Combined Methodology & Overview */}
        <div className="grid md:grid-cols-2 gap-8 items-center">
          <Reveal className="h-full" width="100%">
            <MethodologySection />
          </Reveal>
          <Reveal className="h-full" delay={200} width="100%">
            <ProjectOverviewSection />
          </Reveal>
        </div>

        <Reveal width="100%">
          <MarketAnalysisSection />
        </Reveal>

        <div className="space-y-32">
          {/* Pair 1: Problem & Identified Problems */}
          <div className="grid md:grid-cols-2 gap-12 items-stretch">
            <Reveal className="h-full" width="100%">
              <ProblemStatementSection />
            </Reveal>
            <Reveal className="h-full" delay={200} width="100%">
              <IdentifiedProblemsSection />
            </Reveal>
          </div>

          <Reveal width="100%">
            <UserSurveySection />
          </Reveal>

          {/* Pair 2: Tech Drawing & Design Detailing */}
          <div className="grid md:grid-cols-2 gap-12 items-stretch">
            <Reveal className="h-full" width="100%">
              <TechnicalDrawingSection />
            </Reveal>
            <Reveal className="h-full" delay={200} width="100%">
              <DesignDetailingSection />
            </Reveal>
          </div>

          {/* <Reveal width="100%">
            <BOMSection />
          </Reveal> */}

          <Reveal width="100%">
            <VideoSection />
          </Reveal>

          {/* Pair 3: Utility & Team */}
          <div className="grid md:grid-cols-2 gap-12 items-stretch">
            <Reveal className="h-full" width="100%">
              <UtilitySection />
            </Reveal>
            <Reveal className="h-full" delay={200} width="100%">
              <TeamSection />
            </Reveal>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
