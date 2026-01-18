"use client";

import React from "react";
import "./FloatingBlocks.css";

export function FloatingBlocks() {
    return (
        <ul className="floating-blocks">
            {Array.from({ length: 10 }).map((_, i) => (
                <li key={i}></li>
            ))}
        </ul>
    );
}
