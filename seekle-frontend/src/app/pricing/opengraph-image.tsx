// src/app/pricing/opengraph-image.tsx
import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Pricing | Seekle";
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
            Pricing
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
              Starter is live.
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
            Simple credits-based pricing. 1 credit = 1 search. No hidden limits.
          </div>
        </div>

        {/* Cards */}
        <div
          style={{
            display: "flex",
            gap: 18,
            marginTop: 18,
          }}
        >
          {/* Starter */}
          <div
            style={{
              flex: 1,
              borderRadius: 24,
              background: "#ffffff",
              border: "1px solid #e4e4e7",
              boxShadow:
                "0 1px 2px rgba(16,24,40,0.06), 0 1px 3px rgba(16,24,40,0.10)",
              padding: 22,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <div style={{ fontSize: 16, color: "#52525b" }}>Starter</div>
              <div
                style={{
                  fontSize: 12,
                  color: "#52525b",
                  background: "#f6f1e8",
                  borderRadius: 999,
                  padding: "6px 10px",
                }}
              >
                Live
              </div>
            </div>
            <div style={{ marginTop: 12, display: "flex", gap: 10 }}>
              <div style={{ fontSize: 40, fontWeight: 800 }}>£6</div>
              <div style={{ paddingTop: 18, color: "#52525b" }}>/ month</div>
            </div>
            <div style={{ marginTop: 10, fontSize: 16, color: "#3f3f46" }}>
              200 credits / month
            </div>
            <div style={{ marginTop: 6, fontSize: 13, color: "#52525b" }}>
              ChatGPT · Perplexity · Gemini · Claude · Grok
            </div>
          </div>

          {/* Pro */}
          <div
            style={{
              flex: 1,
              borderRadius: 24,
              background: "rgba(255,255,255,0.7)",
              border: "1px solid #e4e4e7",
              padding: 22,
            }}
          >
            <div style={{ fontSize: 16, color: "#52525b" }}>Pro</div>
            <div style={{ marginTop: 18, fontSize: 28, fontWeight: 750 }}>
              Coming soon
            </div>
            <div style={{ marginTop: 10, fontSize: 14, color: "#52525b" }}>
              More features + workflows
            </div>
          </div>

          {/* Power */}
          <div
            style={{
              flex: 1,
              borderRadius: 24,
              background: "rgba(255,255,255,0.7)",
              border: "1px solid #e4e4e7",
              padding: 22,
            }}
          >
            <div style={{ fontSize: 16, color: "#52525b" }}>Power</div>
            <div style={{ marginTop: 18, fontSize: 28, fontWeight: 750 }}>
              Coming soon
            </div>
            <div style={{ marginTop: 10, fontSize: 14, color: "#52525b" }}>
              Advanced tools + integrations
            </div>
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
            Secure checkout via Stripe
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
            seekle.io/pricing
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
