"use client";

import React from "react";

declare global {
  interface Window {
    turnstile?: any;
  }
}

type Props = {
  siteKey: string;
  onToken: (token: string) => void;
  className?: string;
};

export default function Turnstile({ siteKey, onToken, className }: Props) {
  const ref = React.useRef<HTMLDivElement | null>(null);
  const widgetIdRef = React.useRef<string | null>(null);

  React.useEffect(() => {
    if (!siteKey) return;

    const ensureScript = () =>
      new Promise<void>((resolve) => {
        if (document.getElementById("turnstile-script")) return resolve();
        const s = document.createElement("script");
        s.id = "turnstile-script";
        s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        s.async = true;
        s.defer = true;
        s.onload = () => resolve();
        document.head.appendChild(s);
      });

    let cancelled = false;

    (async () => {
      await ensureScript();
      if (cancelled) return;

      // Wait for Turnstile to be ready
      const waitReady = () =>
        new Promise<void>((resolve) => {
          const tick = () => {
            if (window.turnstile?.render) return resolve();
            setTimeout(tick, 50);
          };
          tick();
        });

      await waitReady();
      if (cancelled) return;

      if (!ref.current) return;

      // If already rendered, don’t re-render
      if (widgetIdRef.current) return;

      const id = window.turnstile.render(ref.current, {
        sitekey: siteKey,
        callback: (token: string) => onToken(token),
        "expired-callback": () => onToken(""),
        "error-callback": () => onToken(""),
        theme: "light",
        size: "compact",
      });

      widgetIdRef.current = id;
    })();

    return () => {
      cancelled = true;
      try {
        if (widgetIdRef.current && window.turnstile?.remove) {
          window.turnstile.remove(widgetIdRef.current);
        }
      } catch {}
      widgetIdRef.current = null;
    };
  }, [siteKey, onToken]);

  return <div className={className} ref={ref} />;
}
