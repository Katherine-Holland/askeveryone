export const metadata = {
  title: "Contact | Seekle",
  description: "Contact Seekle for support, feedback, or bug reports.",
};

export default function ContactPage() {
  const email = "support@seekle.ai";

  return (
    <main
      style={{
        maxWidth: 720,
        margin: "0 auto",
        padding: "64px 24px",
        lineHeight: 1.6,
        color: "#1F2933",
        background: "#ffffff",
      }}
    >
      <h1 style={{ fontSize: "2.2rem", marginBottom: "0.5rem" }}>Contact</h1>

      <p style={{ margin: "0.75rem 0" }}>
        If you have a support question, feedback, or would like to report a bug, please contact us using the email
        address below.
      </p>

      <div
        style={{
          marginTop: 24,
          padding: "16px 18px",
          borderRadius: 12,
          background: "#F5F7F9",
          border: "1px solid #E3E7EB",
          fontSize: "1rem",
        }}
      >
        <strong>Email:</strong>{" "}
        <a
          href={`mailto:${email}`}
          style={{
            color: "#0F766E",
            textDecoration: "none",
            fontWeight: 600,
          }}
        >
          {email}
        </a>
      </div>

      <p style={{ margin: "0.75rem 0", marginTop: 18 }}>
        We aim to respond as quickly as possible during normal business hours.
      </p>

      <div style={{ marginTop: 32, fontSize: "0.9rem", color: "#555" }}>
        <p style={{ margin: 0 }}>
          Seekle is intended for users aged <strong>18 or older</strong>.
        </p>
      </div>
    </main>
  );
}
