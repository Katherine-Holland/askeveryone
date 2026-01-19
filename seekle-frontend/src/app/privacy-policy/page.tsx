export const metadata = {
  title: "Privacy Policy | Seekle",
  description: "Seekle Privacy Policy (GDPR-aligned) and age (18+) requirement.",
};

export default function PrivacyPolicyPage() {
  const effectiveDate = "[Insert Date]";
  const lastUpdated = "[Insert Date]";

  return (
    <main style={{ maxWidth: 860, margin: "0 auto", padding: "48px 20px", lineHeight: 1.65 }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 34, margin: 0 }}>Privacy Policy</h1>
        <p style={{ marginTop: 10, marginBottom: 0 }}>
          <strong>Effective Date:</strong> {effectiveDate}
          <br />
          <strong>Last Updated:</strong> {lastUpdated}
        </p>
      </header>

      <section>
        <h2>1. Introduction</h2>
        <p>
          Seekle (“we”, “our”, or “us”) is committed to protecting your privacy and handling personal data responsibly.
          This Privacy Policy explains how we collect, use, store, and protect personal information when you use the
          Seekle platform, website, or related services.
        </p>
        <p>By using Seekle, you agree to the practices described in this policy.</p>
      </section>

      <section>
        <h2>2. Eligibility (18+ Only)</h2>
        <p>
          Seekle is intended for users aged <strong>18 or older</strong>. We do not knowingly collect or process
          personal data from individuals under the age of 18. If we become aware that such data has been collected, it
          will be deleted promptly.
        </p>
      </section>

      <section>
        <h2>3. Information We Collect</h2>
        <h3>3.1 Information You Provide</h3>
        <ul>
          <li>Name and email address</li>
          <li>Account and login information</li>
          <li>Company or website details (if provided)</li>
          <li>Communications with Seekle (e.g., support requests)</li>
        </ul>

        <h3>3.2 Automatically Collected Information</h3>
        <ul>
          <li>IP address</li>
          <li>Browser type and device information</li>
          <li>Usage data related to platform features</li>
          <li>Log and performance data</li>
        </ul>

        <h3>3.3 AI &amp; Platform Data</h3>
        <p>
          Seekle does <strong>not</strong> collect or store customer API keys for third-party AI services. We do not
          sell personal data. Unless explicitly required for a specific feature, Seekle is not designed to collect
          sensitive personal information.
        </p>
      </section>

      <section>
        <h2>4. How We Use Your Data</h2>
        <p>We use personal data only to:</p>
        <ul>
          <li>Provide and operate the Seekle platform</li>
          <li>Improve performance, reliability, and user experience</li>
          <li>Monitor platform security and misuse</li>
          <li>Communicate service updates</li>
          <li>Comply with legal obligations</li>
        </ul>
        <p>We do not sell or rent personal data.</p>
      </section>

      <section>
        <h2>5. AI &amp; Automated Processing</h2>
        <p>Seekle may use AI systems to generate insights and reports. In doing so:</p>
        <ul>
          <li>AI processing is feature-limited and controlled</li>
          <li>AI outputs are generated from structured inputs and constrained workflows</li>
          <li>We do not provide unrestricted AI access through Seekle</li>
          <li>We do not use customer data to train third-party models</li>
        </ul>
      </section>

      <section>
        <h2>6. Data Sharing</h2>
        <p>We may share limited data with:</p>
        <ul>
          <li>Infrastructure providers (hosting, analytics, security)</li>
          <li>AI service providers (via official APIs only, where relevant to a feature)</li>
          <li>Legal authorities where required by law</li>
        </ul>
        <p>
          Where we use service providers, we require appropriate contractual safeguards and data protection standards.
        </p>
      </section>

      <section>
        <h2>7. Data Retention</h2>
        <p>
          We retain personal data only for as long as necessary to provide the service, meet legal or regulatory
          obligations, resolve disputes, and enforce agreements. Users may request deletion of their data at any time.
        </p>
      </section>

      <section>
        <h2>8. Data Security</h2>
        <p>
          We implement reasonable technical and organizational measures to protect data, including access controls,
          encrypted communications, secure credential handling, and monitoring/logging. No system is completely secure,
          but we take appropriate steps to reduce risk.
        </p>
      </section>

      <section>
        <h2>9. Your Rights (GDPR)</h2>
        <p>Where GDPR applies, you may have the right to:</p>
        <ul>
          <li>Access your data</li>
          <li>Correct inaccurate data</li>
          <li>Request deletion</li>
          <li>Restrict or object to processing</li>
          <li>Request data portability</li>
        </ul>
        <p>
          To exercise these rights, contact: <a href="mailto:support@seekle.io">support@seekle.io</a>
        </p>
      </section>

      <section>
        <h2>10. Cookies &amp; Tracking</h2>
        <p>
          Seekle uses limited cookies or similar technologies for authentication, security, and performance monitoring.
          We do not use third-party advertising trackers.
        </p>
      </section>

      <section>
        <h2>11. Third-Party Links</h2>
        <p>
          Seekle may contain links to third-party services. We are not responsible for the privacy practices of those
          services.
        </p>
      </section>

      <section>
        <h2>12. Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. Material changes will be communicated via the platform
          or website. The “Last Updated” date will reflect the most recent version.
        </p>
      </section>

      <section>
        <h2>13. Contact</h2>
        <p>
          For privacy-related questions or requests, contact:{" "}
          <a href="mailto:support@seekle.io">support@seekle.io</a>
        </p>
      </section>
      <div className="mt-10 text-xs text-zinc-500">
          <a
            href="/"
            className="underline underline-offset-2 hover:text-zinc-700"
          >
            ← Back to Seekle
          </a>
        </div>
    </main>
  );
}
