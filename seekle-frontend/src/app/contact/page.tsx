export const metadata = {
  title: "Contact | Seekle",
  description: "Contact Seekle for support, feedback, or bug reports.",
};

type Category = "Support" | "Feedback" | "Bug";

export default function ContactPage() {
  // This page uses a mailto: submit so it works without any backend.
  // Later, you can replace it with a POST to an API route (e.g. /api/contact).
  const supportEmail = "support@seekle.ai";

  return (
    <main style={{ maxWidth: 860, margin: "0 auto", padding: "48px 20px", lineHeight: 1.65 }}>
      <header style={{ marginBottom: 18 }}>
        <h1 style={{ fontSize: 34, margin: 0 }}>Contact</h1>
        <p style={{ marginTop: 10, marginBottom: 0 }}>
          For support requests, feedback, or bug reports, email{" "}
          <a href={`mailto:${supportEmail}`}>{supportEmail}</a>
          <br />
          Or use the form below (it will open your email client).
        </p>
      </header>

      <section style={{ marginTop: 28 }}>
        <h2 style={{ marginBottom: 10 }}>Send a message</h2>

        <ContactForm supportEmail={supportEmail} />
      </section>

      <section style={{ marginTop: 28 }}>
        <h2 style={{ marginBottom: 10 }}>Bug reports (recommended details)</h2>
        <ul style={{ marginTop: 0 }}>
          <li>What you expected to happen vs what happened</li>
          <li>Steps to reproduce (1, 2, 3…)</li>
          <li>Screenshot or screen recording (if possible)</li>
          <li>Your browser/device and approximate time it occurred</li>
          <li>Any error message shown</li>
        </ul>
      </section>

      <section style={{ marginTop: 28 }}>
        <h2 style={{ marginBottom: 10 }}>Service note</h2>
        <p style={{ marginTop: 0 }}>
          Seekle is intended for users aged <strong>18 or older</strong>. If you believe someone under 18 has provided
          personal data to Seekle, please notify us at{" "}
          <a href={`mailto:${supportEmail}`}>{supportEmail}</a>.
        </p>
      </section>
    </main>
  );
}

function ContactForm({ supportEmail }: { supportEmail: string }) {
  // Inline JS-free approach: build mailto on submit
  // (Works without adding "use client" only if we avoid event handlers.)
  // To keep it simple and functional, we’ll use a plain mailto link approach below.
  // Users can also just email directly.

  const categories: Category[] = ["Support", "Feedback", "Bug"];

  return (
    <form
      action={`mailto:${supportEmail}`}
      method="post"
      encType="text/plain"
      style={{
        border: "1px solid rgba(31,41,51,0.15)",
        borderRadius: 14,
        padding: 18,
      }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="name">
            <strong>Name</strong> (optional)
          </label>
          <input
            id="name"
            name="name"
            placeholder="Your name"
            style={inputStyle}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="email">
            <strong>Email</strong> (optional)
          </label>
          <input
            id="email"
            name="email"
            placeholder="you@company.com"
            style={inputStyle}
          />
        </div>
      </div>

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
        <label htmlFor="category">
          <strong>Category</strong>
        </label>
        <select id="category" name="category" defaultValue="Support" style={inputStyle}>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
        <label htmlFor="subject">
          <strong>Subject</strong>
        </label>
        <input
          id="subject"
          name="subject"
          placeholder="e.g., Billing question / Bug on dashboard / Feature request"
          style={inputStyle}
          required
        />
      </div>

      <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
        <label htmlFor="message">
          <strong>Message</strong>
        </label>
        <textarea
          id="message"
          name="message"
          placeholder="Tell us what’s going on…"
          rows={7}
          style={{ ...inputStyle, resize: "vertical" }}
          required
        />
      </div>

      <div style={{ marginTop: 14, display: "flex", gap: 10, alignItems: "center" }}>
        <button type="submit" style={buttonStyle}>
          Open email to send
        </button>
        <span style={{ fontSize: 13, opacity: 0.8 }}>
          This will open your email client addressed to {supportEmail}.
        </span>
      </div>
    </form>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: 12,
  border: "1px solid rgba(31,41,51,0.18)",
  outline: "none",
};

const buttonStyle: React.CSSProperties = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid rgba(31,41,51,0.2)",
  background: "rgba(31,41,51,0.06)",
  cursor: "pointer",
};
