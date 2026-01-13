"use client";

import React from "react";

type Mode = "listening" | "thinking" | "answered";

export default function SeekleRipple({
  mode = "listening",
  size = 110,
  color = "rgba(124, 95, 76, 0.85)", // taupe
}: {
  mode?: Mode;
  size?: number;
  color?: string;
}) {
  // Flow like water: no abrupt jumps — just gentle speed/opacity changes.
  const dur =
    mode === "thinking" ? "1.25s" : mode === "answered" ? "2.6s" : "2.05s";

  const ringOpacityFrom =
    mode === "thinking" ? 0.40 : mode === "answered" ? 0.18 : 0.26;

  const ringOpacityTo =
    mode === "thinking" ? 0.0 : mode === "answered" ? 0.0 : 0.0;

  // Keep radii proportional to the viewBox (0..40)
  const rFrom = mode === "thinking" ? 7.6 : mode === "answered" ? 8.6 : 8.2;
  const rTo = mode === "thinking" ? 19.6 : mode === "answered" ? 19.0 : 19.2;

  // Stroke width can soften the feel
  const strokeWidth = mode === "thinking" ? 1.8 : 1.6;

  // Overall wrapper opacity:
  const wrapperOpacity = mode === "answered" ? 0.55 : 1;

  return (
    <div
      aria-hidden="true"
      className="mx-auto mt-4 mb-1"
      style={{
        width: size,
        height: size,
        opacity: wrapperOpacity,
        transition: "opacity 650ms cubic-bezier(0.16, 1, 0.3, 1)",
        pointerEvents: "none",
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        xmlns="http://www.w3.org/2000/svg"
        style={{ display: "block" }}
      >
        {/* Ring A */}
        <circle
          cx="20"
          cy="20"
          fill="none"
          r={rFrom}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        >
          <animate
            attributeName="r"
            from={String(rFrom)}
            to={String(rTo)}
            dur={dur}
            begin="0s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            from={String(ringOpacityFrom)}
            to={String(ringOpacityTo)}
            dur={dur}
            begin="0s"
            repeatCount="indefinite"
          />
        </circle>

        {/* Ring B (delayed) */}
        <circle
          cx="20"
          cy="20"
          fill="none"
          r={rFrom}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        >
          <animate
            attributeName="r"
            from={String(rFrom)}
            to={String(rTo)}
            dur={dur}
            begin={`calc(${dur} / 2)`}
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            from={String(ringOpacityFrom)}
            to={String(ringOpacityTo)}
            dur={dur}
            begin={`calc(${dur} / 2)`}
            repeatCount="indefinite"
          />
        </circle>
      </svg>
    </div>
  );
}
