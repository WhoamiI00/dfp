"use client";

import React from "react";

const codeSnippet = `
// IVEN-TRON Main Control Logic
// Warehouse Management System v1.0

package com.iventron.controller;

import java.util.ArrayList;
import java.util.List;

public class MainController {

    private static final int MAX_ROBOTS = 5;
    private List<Robot> fleet;
    private InventoryManager inventory;

    public void init() {
        System.out.println("Initializing IVEN-TRON WMS...");
        fleet = new ArrayList<>();
        inventory = new InventoryManager();
        
        // Initialize Fleet
        for (int i = 0; i < MAX_ROBOTS; i++) {
            fleet.add(new Robot("BOT-" + i));
        }
        
        connectToDashboard();
    }

    public void run() {
        while (true) {
            // 1. Process Order Queue
            Order order = OrderQueue.getNext();
            if (order != null) {
                assignTask(order);
            }

            // 2. Telemetry Loop
            for (Robot bot : fleet) {
                bot.updateStatus();
                if (bot.isLowBattery()) {
                    bot.returnToCharger();
                }
            }

            // 3. AI Demand Prediction
            if (Time.isEndOfDay()) {
                DemandModel.predictNextDay();
            }
            
            try { Thread.sleep(100); } catch (Exception e) {}
        }
    }

    private void assignTask(Order order) {
        Robot availableBot = fleet.stream()
            .filter(Robot::isIdle)
            .findFirst()
            .orElse(null);
            
        if (availableBot != null) {
            System.out.println("Assigning " + order.id + " to " + availableBot.id);
            availableBot.dispatch(order.targetLocation);
        } else {
            OrderQueue.requeue(order);
        }
    }
}
`;

export function CodeScroller() {
  return (
    <div className="h-full bg-[#0d1117] border border-white/10 rounded-xl overflow-hidden relative group font-mono text-xs">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-white/5 border-b border-white/5">
            <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
                <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
            </div>
            <span className="text-white/40 text-[10px] tracking-widest uppercase">main.java</span>
        </div>

        {/* Code Content - Auto Scrolling */}
        <div className="overflow-hidden h-[300px] md:h-full relative opacity-80 group-hover:opacity-100 transition-opacity">
            <div className="absolute top-0 left-0 w-full animate-scroll-vertical">
                <pre className="p-4 text-orange-200/90 leading-relaxed whitespace-pre-wrap">
                    {codeSnippet}
                    {/* Repeat for seamless loop */}
                    {codeSnippet}
                </pre>
            </div>
        </div>

        {/* Overlay Gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#0d1117]/80 pointer-events-none" />
    </div>
  );
}
