"use client";

import React from "react";

type Mode = "listening" | "thinking" | "answered";

export default function SeekleRipple({
  mode = "listening",
  size = 140, // ⬅️ bigger
  color = "rgba(124, 95, 76, 0.35)", // ⬅️ slightly softer taupe
}: {
  mode?: Mode;
  size?: number;
  color?: string;
}) {
  const dur =
    mode === "thinking" ? "1.4s" : mode === "answered" ? "2.8s" : "2.3s";

  // Softer centre — start rings further out + lower opacity
  const ringOpacityFrom =
    mode === "thinking" ? 0.28 : mode === "answered" ? 0.14 : 0.18;

  const ringOpacityTo = 0;

  // ⬅️ larger starting radius = less dense middle
  const rFrom = mode === "thinking" ? 9.5 : mode === "answered" ? 10.5 : 10;
  const rTo = mode === "thinking" ? 22 : mode === "answered" ? 21.5 : 21.8;

  // ⬅️ thinner stroke for elegance
  const strokeWidth = 1.4;

  const wrapperOpacity = mode === "answered" ? 0.6 : 1;

  return (
    <div
      aria-hidden="true"
      className="mx-auto mt-6 mb-2"
      style={{
        width: size,
        height: size,
        opacity: wrapperOpacity,
        transition: "opacity 700ms cubic-bezier(0.16, 1, 0.3, 1)",
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
        {/* Ripple A */}
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

        {/* Ripple B (offset) */}
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
