import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Seekle — Ask Everyone",
  description: "Ask once. Get answers from everywhere.",

  metadataBase: new URL("https://seekle.io"),

  openGraph: {
    title: "Seekle — Ask Everyone",
    description: "Ask once. Get answers from everywhere.",
    url: "https://seekle.io",
    siteName: "Seekle",
    type: "website",
    images: [
      {
        url: "/og.png", // optional but recommended
        width: 1200,
        height: 630,
        alt: "Seekle — Ask Everyone",
      },
    ],
  },

  twitter: {
    card: "summary_large_image",
    title: "Seekle — Ask Everyone",
    description: "Ask once. Get answers from everywhere.",
    images: ["/og.png"],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} bg-zinc-50 text-zinc-900 antialiased`}
      >
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }}
        />
        {children}
      </body>
    </html>
  );
}
