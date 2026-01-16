// src/app/ai-policy/page.tsx
export default function AIPolicyPage() {
  return (
    <main className="min-h-screen bg-seekle-cream text-seekle-text">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <div className="mb-10">
          <h1 className="text-4xl font-semibold tracking-tight">
            LLM Compliance Policy
          </h1>
          <div className="mt-3 text-sm text-zinc-600 space-y-1">
            <div>
              <span className="font-medium text-seekle-text">
                Effective Date:
              </span>{" "}
              Jan 2026
            </div>
            <div>
              <span className="font-medium text-seekle-text">Applies to:</span>{" "}
              All Seekle services, systems, and personnel
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-seekle-border bg-white p-7 leading-7">
          <Section title="1. Purpose">
            <p>
              This policy defines how Seekle accesses, uses, and governs Large
              Language Models (LLMs) and related AI systems.
            </p>
            <p className="mt-4">The objectives of this policy are to:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Ensure compliant use of third-party AI services</li>
              <li>Prevent misuse or abuse of LLMs via the Seekle platform</li>
              <li>
                Maintain alignment with provider terms, intent, and billing
                models
              </li>
              <li>Support security, availability, and auditability requirements</li>
            </ul>
          </Section>

          <Divider />

          <Section title="2. Scope">
            <p>This policy applies to:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>All AI-powered features offered by Seekle</li>
              <li>All internal systems invoking LLMs or AI services</li>
              <li>
                All employees, contractors, and systems acting on behalf of
                Seekle
              </li>
            </ul>
          </Section>

          <Divider />

          <Section title="3. Policy Principles">
            <SubTitle>3.1 Outcome-Based AI Use</SubTitle>
            <p>
              Seekle uses LLMs solely as internal components within defined
              product features.
            </p>
            <p className="mt-4">Seekle does not:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Provide direct access to LLMs</li>
              <li>Act as an AI proxy, relay, or general-purpose execution layer</li>
              <li>Allow unrestricted or user-defined AI workflows</li>
            </ul>
            <p className="mt-4">
              Users interact only with feature outputs, not underlying models.
            </p>
          </Section>

          <Divider />

          <Section title="4. Access Control &amp; Identity">
            <SubTitle>4.1 Authentication</SubTitle>
            <p>All LLM-backed functionality requires authenticated access.</p>
            <p className="mt-4">Each request is associated with:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>A valid user account</li>
              <li>An approved product feature</li>
              <li>A traceable execution context</li>
            </ul>

            <SubTitle className="mt-6">4.2 Prohibited Access</SubTitle>
            <p>Seekle does not permit:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Anonymous LLM access</li>
              <li>Programmatic or automated access outside approved features</li>
              <li>Direct user-supplied prompts to LLMs</li>
            </ul>
          </Section>

          <Divider />

          <Section title="5. Feature-Bounded Execution">
            <SubTitle>5.1 Controlled Inputs</SubTitle>
            <p>All LLM interactions are:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Internally generated</li>
              <li>Template-based</li>
              <li>Parameterized and schema-constrained</li>
            </ul>
            <p className="mt-4">
              User input is treated as data, not executable instructions.
            </p>

            <SubTitle className="mt-6">5.2 Predictable Outputs</SubTitle>
            <p>LLM outputs are validated and processed to ensure:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Consistency</li>
              <li>Predictability</li>
              <li>Alignment with the intended feature purpose</li>
            </ul>
          </Section>

          <Divider />

          <Section title="6. Provider Access &amp; Usage">
            <SubTitle>6.1 Approved Access Methods</SubTitle>
            <p>Seekle accesses LLMs only through:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Official, documented APIs</li>
              <li>Supported SDKs and authentication methods</li>
            </ul>

            <SubTitle className="mt-6">6.2 Prohibited Practices</SubTitle>
            <p>Seekle will not:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Spoof first-party tools or CLIs</li>
              <li>Use undocumented endpoints or headers</li>
              <li>Bypass billing, throttling, or quota controls</li>
              <li>Misrepresent usage as consumer or interactive traffic</li>
            </ul>
          </Section>

          <Divider />

          <Section title="7. Credential &amp; Key Management">
            <p>Seekle does not:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Accept or store customer-owned LLM API keys</li>
              <li>Relay third-party credentials on behalf of users</li>
            </ul>
            <p className="mt-4">All provider credentials are:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Managed centrally by Seekle</li>
              <li>Access-controlled and monitored</li>
              <li>Used solely for approved platform functionality</li>
            </ul>
          </Section>

          <Divider />

          <Section title="8. Usage Proportionality &amp; Rate Limiting">
            <p>Each AI-powered feature has defined:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Expected token usage ranges</li>
              <li>Execution time limits</li>
              <li>Invocation frequency limits</li>
            </ul>
            <p className="mt-4">Controls include:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Feature-level rate limiting</li>
              <li>User-level usage caps</li>
              <li>Automatic throttling of anomalous behavior</li>
            </ul>
          </Section>

          <Divider />

          <Section title="9. Caching &amp; Load Management">
            <p>Seekle implements caching mechanisms to:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Reduce redundant LLM requests</li>
              <li>Prevent excessive upstream load</li>
              <li>Improve availability and cost predictability</li>
            </ul>
            <p className="mt-4">
              Caching is used in accordance with feature accuracy requirements
              and data handling standards.
            </p>
          </Section>

          <Divider />

          <Section title="10. Automation Controls">
            <SubTitle>10.1 Permitted Automation</SubTitle>
            <p>Automation is limited to:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Scheduled reports</li>
              <li>Periodic refresh operations</li>
              <li>System-controlled background tasks</li>
            </ul>

            <SubTitle className="mt-6">10.2 Prohibited Automation</SubTitle>
            <p>Seekle does not allow:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>User-defined agents or loops</li>
              <li>Arbitrary job execution</li>
              <li>Long-running autonomous workflows</li>
            </ul>
            <p className="mt-4">All automation is auditable and rate-limited.</p>
          </Section>

          <Divider />

          <Section title="11. Crawling &amp; Data Collection">
            <p>Seekle commits to responsible data collection practices, including:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Compliance with robots.txt and crawl directives</li>
              <li>Transparent and consistent user-agent identification</li>
              <li>Reasonable request rates</li>
            </ul>
            <p className="mt-4">
              Seekle does not engage in stealth, proxy, or deceptive crawling behavior.
            </p>
          </Section>

          <Divider />

          <Section title="12. Monitoring &amp; Enforcement">
            <SubTitle>12.1 Monitoring</SubTitle>
            <p>Seekle monitors:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Feature-level usage patterns</li>
              <li>Token consumption</li>
              <li>Repetition and anomaly indicators</li>
            </ul>

            <SubTitle className="mt-6">12.2 Enforcement</SubTitle>
            <p>Violations of this policy may result in:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Warning</li>
              <li>Throttling</li>
              <li>Temporary suspension</li>
              <li>Termination of access, where necessary</li>
            </ul>
          </Section>

          <Divider />

          <Section title="13. Review &amp; Updates">
            <p>This policy is reviewed periodically and updated to reflect:</p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Changes in provider terms</li>
              <li>Regulatory developments</li>
              <li>Platform architecture evolution</li>
            </ul>
          </Section>

          <Divider />

          <Section title="14. Policy Statement">
            <p className="font-medium text-seekle-text">
              Seekle is designed to operate within provider intent, not around it.
            </p>
            <p className="mt-4">
              Features that rely on:
            </p>
            <ul className="mt-2 list-disc pl-6 space-y-1 text-zinc-700">
              <li>Undocumented behavior</li>
              <li>Misrepresentation of usage</li>
              <li>Circumvention of safeguards</li>
            </ul>
            <p className="mt-4">are not permitted.</p>
          </Section>

          <Divider />

          <Section title="Contact">
            <p>
              Questions regarding this policy may be directed to:{" "}
              <a
                href="mailto:support@seekle.io"
                className="text-seekle-brown underline underline-offset-2 hover:text-seekle-brownHover"
              >
                support@seekle.io
              </a>
              .
            </p>
          </Section>
        </div>

        <div className="mt-10 text-xs text-zinc-500">
          <a
            href="/"
            className="underline underline-offset-2 hover:text-zinc-700"
          >
            ← Back to Seekle
          </a>
        </div>
      </div>
    </main>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-lg font-semibold text-seekle-text">{title}</h2>
      <div className="mt-2 text-sm text-zinc-700">{children}</div>
    </section>
  );
}

function SubTitle({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <h3 className={`text-sm font-semibold text-seekle-text ${className}`}>
      {children}
    </h3>
  );
}

function Divider() {
  return <hr className="my-7 border-seekle-border" />;
}
