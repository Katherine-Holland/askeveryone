// src/app/about/page.tsx
import type { Metadata } from "next";

function BreadcrumbJsonLd() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "Home",
        item: "https://seekle.io/",
      },
      {
        "@type": "ListItem",
        position: 2,
        name: "About",
        item: "https://seekle.io/about",
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}


export const metadata: Metadata = {
  title: "About Seekle | Ask Everyone",
  description:
    "Seekle is an Answer Engine Optimization (AEO) platform that helps people find the best answer by querying multiple AI/search providers and returning a single, cited result.",
  alternates: { canonical: "/about" },
  openGraph: {
    title: "About Seekle | Ask Everyone",
    description:
      "Seekle queries multiple providers to produce a single best answer with sources. Built for AEO: clarity, citations, and measurable outcomes.",
    url: "/about",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "About Seekle | Ask Everyone",
    description:
      "Seekle queries multiple providers to produce a single best answer with sources. Built for AEO.",
  },
};

function FAQJsonLd() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "What is Seekle?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Seekle is an Answer Engine Optimization (AEO) platform that helps you get the best possible answer by querying multiple AI/search providers and returning one clear response with sources.",
        },
      },
      {
        "@type": "Question",
        name: "What does “Ask Everyone” mean?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "It means Seekle can route a question to more than one provider and select the strongest, most relevant response—so you’re not limited to a single model’s viewpoint.",
        },
      },
      {
        "@type": "Question",
        name: "Do answers include sources?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Yes. When available, Seekle shows citations so you can verify key claims and continue reading the original sources.",
        },
      },
      {
        "@type": "Question",
        name: "How does pricing work?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Seekle uses credits. In the Starter plan, 1 credit equals 1 search. Plans allocate a monthly credit balance.",
        },
      },
      {
        "@type": "Question",
        name: "Is Seekle for SEO or AEO?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "Seekle is built for AEO — helping content surface in AI-generated answers through clarity, structure, and citations.",
        },
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}

export default function AboutPage() {
  return (
    <main className="min-h-screen bg-seekle-cream text-seekle-text">
      <BreadcrumbJsonLd />
      <FAQJsonLd />

      <div className="mx-auto max-w-4xl px-6 py-14">
        {/* Back link */}
        <div className="mb-6">
          <a
            href="/"
            className="text-sm text-zinc-500 hover:text-zinc-700 underline underline-offset-2"
          >
            ← Back to Seekle
          </a>
        </div>

        {/* Header */}
        <header className="text-center">
          <p className="text-xs tracking-widest text-zinc-500 uppercase">
            About Seekle
          </p>

          {/* Smaller headline */}
          <h1 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight">
            Ask Everyone
          </h1>

          <p className="mt-4 text-base text-zinc-600">
            Seekle is an <strong>Answer Engine Optimization (AEO)</strong>{" "}
            platform that queries multiple AI systems and returns{" "}
            <strong>one clear answer</strong> with{" "}
            <strong>verifiable sources</strong>.
          </p>
        </header>

        <section className="mt-12 grid gap-6">
          <div className="rounded-2xl border border-seekle-border bg-white p-6">
            <h2 className="text-xl font-semibold">What Seekle does</h2>
            <ul className="mt-3 space-y-2 text-sm text-zinc-700 leading-6">
              <li>
                <strong>Routes your question</strong> to the most suitable
                provider (or multiple providers when needed).
              </li>
              <li>
                <strong>Returns a single best answer</strong> designed to be
                readable and action-oriented.
              </li>
              <li>
                <strong>Includes citations</strong> (when available) so you can
                validate claims and go deeper.
              </li>
              <li>
                <strong>Tracks usage via credits</strong> so pricing is simple
                and predictable.
              </li>
            </ul>
          </div>

          <div className="rounded-2xl border border-seekle-border bg-white p-6">
            <h2 className="text-xl font-semibold">
              Why “Answer Engine Optimization” matters
            </h2>
            <p className="mt-3 text-sm text-zinc-700 leading-7">
              People increasingly discover products, services, and information
              through AI answers. AEO is about making your content easier for AI
              systems to understand, trust, and cite. Seekle is built around
              <strong> clarity, citations, and consistency</strong>—the same
              ingredients that help answers perform well in AI-driven discovery.
            </p>
          </div>

          <div className="rounded-2xl border border-seekle-border bg-white p-6">
            <h2 className="text-xl font-semibold">Who Seekle is for</h2>
            <div className="mt-3 grid gap-4 sm:grid-cols-2 text-sm text-zinc-700 leading-6">
              <div>
                <p className="font-medium text-seekle-text">Founders & teams</p>
                <p className="mt-1 text-zinc-600">
                  Get fast, sourced answers for strategy, research, and
                  decision-making.
                </p>
              </div>
              <div>
                <p className="font-medium text-seekle-text">Marketers</p>
                <p className="mt-1 text-zinc-600">
                  Understand what AI answers look like and how to improve
                  content for AEO.
                </p>
              </div>
              <div>
                <p className="font-medium text-seekle-text">Operators</p>
                <p className="mt-1 text-zinc-600">
                  Reduce time spent cross-checking across tools and tabs.
                </p>
              </div>
              <div>
                <p className="font-medium text-seekle-text">Researchers</p>
                <p className="mt-1 text-zinc-600">
                  Follow citations and compare perspectives quickly.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-12">
          <h2 className="text-2xl font-semibold tracking-tight">FAQ</h2>

          <div className="mt-4 space-y-3">
            {[
              {
                q: "What is Seekle?",
                a: "Seekle is an Answer Engine Optimization (AEO) platform that helps you get the best possible answer by querying multiple AI/search providers and returning one clear response with sources.",
              },
              {
                q: "What does “Ask Everyone” mean?",
                a: "It means Seekle can route a question to more than one provider and select the strongest response—so you’re not limited to a single model’s viewpoint or browsing ability.",
              },
              {
                q: "Do answers include sources?",
                a: "Yes. When available, Seekle shows citations so you can verify claims and read the originals.",
              },
              {
                q: "How does pricing work?",
                a: "Seekle uses credits. For Starter, 1 credit = 1 search. Each plan gives you a monthly credit balance.",
              },
              {
                q: "Where can I read your policies?",
                a: "You can view Privacy, Terms, and the LLM Compliance Policy in the footer links.",
              },
            ].map((item) => (
              <details
                key={item.q}
                className="rounded-2xl border border-seekle-border bg-white p-5"
              >
                <summary className="cursor-pointer list-none font-medium text-seekle-text">
                  {item.q}
                </summary>
                <p className="mt-3 text-sm text-zinc-700 leading-7">{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-seekle-border bg-white p-6">
          <h2 className="text-xl font-semibold">Contact</h2>
          <p className="mt-3 text-sm text-zinc-700 leading-7">
            Want to partner, request a feature, or ask a question? Reach out via
            the contact page.
          </p>

          <div className="mt-4 flex flex-wrap gap-3">
            <a
              href="/contact"
              className="inline-flex items-center justify-center rounded-xl bg-seekle-brown px-4 py-2 text-sm text-white hover:bg-seekle-brownHover"
            >
              Contact Seekle
            </a>
            <a
              href="/pricing"
              className="inline-flex items-center justify-center rounded-xl border border-seekle-border bg-white px-4 py-2 text-sm text-seekle-text hover:bg-seekle-muted"
            >
              View pricing
            </a>
          </div>
        </section>

        <footer className="mt-12 text-center text-xs text-zinc-500">
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
            <a className="hover:text-zinc-700" href="/privacy">
              Privacy
            </a>
            <a className="hover:text-zinc-700" href="/terms">
              Terms
            </a>
            <a className="hover:text-zinc-700" href="/ai-policy">
              LLM Compliance Policy
            </a>
          </div>
          <p className="mt-3">© {new Date().getFullYear()} Seekle</p>
        </footer>
      </div>
    </main>
  );
}
