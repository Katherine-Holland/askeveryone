export const metadata = {
  title: "Terms of Service | Seekle",
  description: "Terms of Service for using the Seekle platform.",
};

export default function TermsOfServicePage() {
  return (
    <main
      style={{
        maxWidth: 860,
        margin: "0 auto",
        padding: "64px 24px",
        lineHeight: 1.65,
        color: "#1F2933",
      }}
    >
      <h1 style={{ fontSize: "2.2rem", marginBottom: "0.5rem" }}>
        Terms of Service
      </h1>

      <p>
        <strong>Effective Date:</strong> [Insert Date]
      </p>

      <p>
        These Terms of Service (“Terms”) govern your access to and use of the
        Seekle platform, website, and related services (“Service”). By using
        Seekle, you agree to these Terms.
      </p>

      <h2>1. Eligibility</h2>
      <p>
        Seekle is intended for users aged <strong>18 years or older</strong>.
        By using the Service, you confirm that you meet this requirement.
      </p>

      <h2>2. Use of the Service</h2>
      <p>
        You agree to use Seekle only for lawful purposes and in accordance with
        these Terms. You must not:
      </p>
      <ul>
        <li>Use the Service for unlawful or fraudulent activity</li>
        <li>Attempt to reverse engineer or misuse the platform</li>
        <li>Interfere with or disrupt the Service</li>
        <li>Attempt to access systems or data you are not authorised to access</li>
      </ul>

      <h2>3. AI & Platform Usage</h2>
      <p>
        Seekle uses AI systems to provide insights and functionality. You
        acknowledge that:
      </p>
      <ul>
        <li>AI outputs are generated automatically and may not be error-free</li>
        <li>Seekle does not provide legal, financial, or professional advice</li>
        <li>You are responsible for how you use any outputs provided</li>
      </ul>

      <h2>4. Accounts & Access</h2>
      <p>
        You are responsible for maintaining the confidentiality of your account
        and for all activity that occurs under your account.
      </p>

      <h2>5. Acceptable Use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>Abuse, overload, or attempt to bypass platform limitations</li>
        <li>Use automated tools to access the Service without permission</li>
        <li>Use Seekle in a way that violates third-party terms or laws</li>
      </ul>

      <h2>6. Intellectual Property</h2>
      <p>
        All content, software, and materials provided by Seekle remain the
        intellectual property of Seekle or its licensors.
      </p>
      <p>
        You may not copy, distribute, or modify any part of the Service without
        written permission.
      </p>

      <h2>7. Availability & Changes</h2>
      <p>
        We may modify, suspend, or discontinue any part of the Service at any
        time without notice. We do not guarantee uninterrupted availability.
      </p>

      <h2>8. Disclaimer</h2>
      <p>
        The Service is provided on an “as is” and “as available” basis. Seekle
        makes no warranties of any kind, express or implied, including accuracy,
        reliability, or fitness for a particular purpose.
      </p>

      <h2>9. Limitation of Liability</h2>
      <p>
        To the fullest extent permitted by law, Seekle shall not be liable for
        any indirect, incidental, or consequential damages arising from your
        use of the Service.
      </p>

      <h2>10. Termination</h2>
      <p>
        We reserve the right to suspend or terminate access to the Service if
        these Terms are violated or if misuse is detected.
      </p>

      <h2>11. Privacy</h2>
      <p>
        Your use of the Service is also governed by our{" "}
        <a href="/privacy-policy">Privacy Policy</a>.
      </p>

      <h2>12. Changes to These Terms</h2>
      <p>
        We may update these Terms from time to time. Continued use of the
        Service after changes are posted constitutes acceptance of the updated
        Terms.
      </p>

      <h2>13. Contact</h2>
      <p>
        For questions about these Terms, contact us at{" "}
        <a href="mailto:support@seekle.io">support@seekle.io</a>.
      </p>
    </main>
  );
}
