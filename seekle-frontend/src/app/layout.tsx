import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Script from "next/script";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const orgJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Seekle",
  url: "https://seekle.io",
  logo: "https://seekle.io/icon.png",
  description:
    "Seekle is an AI-powered search and discovery platform that combines multiple LLMs into one interface.",
  sameAs: [
    "https://twitter.com/seekle",
    "https://www.linkedin.com/company/seekleio"
  ],
};

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
      <head>
        {/* Plausible Analytics */}
        <Script
          src="https://plausible.io/js/pa-BdjSFQnvENpcnXY77w1IH.js"
          strategy="afterInteractive"
        />

        <Script id="plausible-init" strategy="afterInteractive">
          {`
            window.plausible = window.plausible || function() {
              (plausible.q = plausible.q || []).push(arguments)
            };
            plausible.init && plausible.init();
          `}
        </Script>
      </head>
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
