// src/app/contact/opengraph-image.tsx
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Contact | Seekle";
export const size = { width: 1200, height: 630 };
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
          position: "relative",
          overflow: "hidden",
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
            Contact
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div
              style={{
                fontSize: 68,
                fontWeight: 800,
                letterSpacing: -1.5,
                lineHeight: 1.05,
              }}
            >
              Seekle
            </div>
            <div
              style={{
                fontSize: 30,
                fontWeight: 650,
                color: "#6b4f3c",
                letterSpacing: -0.4,
              }}
            >
              Support & feedback
            </div>
          </div>

          <div
            style={{
              marginTop: 10,
              fontSize: 22,
              lineHeight: 1.35,
              color: "#3f3f46",
              maxWidth: 980,
            }}
          >
            Get help, report bugs, or share ideas to improve Seekle.
          </div>
        </div>

        {/* Card */}
        <div
          style={{
            borderRadius: 24,
            background: "#ffffff",
            border: "1px solid #e4e4e7",
            boxShadow:
              "0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)",
            padding: 28,
          }}
        >
          <div style={{ fontSize: 16, color: "#52525b" }}>Email</div>
          <div
            style={{
              marginTop: 10,
              fontSize: 34,
              fontWeight: 800,
              letterSpacing: -0.6,
            }}
          >
            support@seekle.io
          </div>
          <div style={{ marginTop: 10, fontSize: 16, color: "#3f3f46" }}>
            We reply as quickly as possible during normal business hours.
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
          <div style={{ fontSize: 16, color: "#52525b" }}>
            Seekle is intended for users aged 18+
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
              fontWeight: 650,
            }}
          >
            seekle.io/contact
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
