// src/app/about/opengraph-image.tsx
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "About Seekle | Ask Everyone";
export const size = {
  width: 1200,
  height: 630,
};

export const contentType = "image/png";

export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "1200px",
          height: "630px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "72px",
          background: "#faf7f2",
          color: "#18181b",
          fontFamily:
            'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, Arial',
        }}
      >
        {/* Top */}
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              fontSize: 14,
              letterSpacing: 3,
              textTransform: "uppercase",
              color: "#52525b",
            }}
          >
            About
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div
              style={{
                fontSize: 72,
                fontWeight: 700,
                letterSpacing: -1.5,
                lineHeight: 1.05,
              }}
            >
              Seekle
            </div>
            <div
              style={{
                fontSize: 34,
                fontWeight: 600,
                color: "#6b4f3c",
                letterSpacing: -0.5,
              }}
            >
              Ask Everyone.
            </div>
          </div>

          <div
            style={{
              marginTop: 10,
              fontSize: 24,
              lineHeight: 1.35,
              color: "#3f3f46",
              maxWidth: 980,
            }}
          >
            One clear answer by querying multiple AI/search providers — with
            sources you can verify.
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            gap: 24,
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 8,
              fontSize: 18,
              color: "#52525b",
            }}
          >
            <div style={{ fontWeight: 600, color: "#18181b" }}>
              Answer Engine Optimization (AEO)
            </div>
            <div>Clarity • Citations • Consistency</div>
          </div>

          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "14px 18px",
              borderRadius: 999,
              background: "#ffffff",
              border: "1px solid #e4e4e7",
              boxShadow:
                "0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)",
              color: "#18181b",
              fontSize: 18,
              fontWeight: 600,
            }}
          >
            seekle.io/about
          </div>
        </div>

        {/* Subtle corner glow */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(circle at 18% 22%, rgba(124,95,76,0.18), rgba(124,95,76,0) 52%)",
          }}
        />
      </div>
    ),
    size
  );
}
