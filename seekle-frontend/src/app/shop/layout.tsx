// seekle-frontend/src/app/shop/layout.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Seekle Shop",
  description: "Shop with preferences + vibes for better results.",
};

export default function ShopLayout({ children }: { children: React.ReactNode }) {
  // Keep it minimal; uses global layout.tsx for overall shell.
  return <>{children}</>;
}
