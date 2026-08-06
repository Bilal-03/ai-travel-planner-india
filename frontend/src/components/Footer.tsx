export default function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--glass-border)",
        background: "var(--cream)",
      }}
    >
      <div
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: "3.5rem 1.75rem 2rem",
        }}
      >
        {/* Top: Logo + Columns */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.5fr repeat(3, 1fr)",
            gap: "2rem",
          }}
          className="footer-grid"
        >
          {/* Logo column */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 28,
                  height: 28,
                  borderRadius: 7,
                  background: "linear-gradient(135deg, var(--rust), var(--marigold))",
                  color: "white",
                  fontSize: "0.7rem",
                  fontWeight: 700,
                }}
              >
                ✦
              </span>
              <span
                style={{
                  fontFamily: "var(--font-playfair, 'Playfair Display', Georgia, serif)",
                  fontWeight: 700,
                  fontSize: "1.2rem",
                  color: "var(--foreground)",
                }}
              >
                Yatra<span style={{ color: "var(--marigold)" }}>AI</span>
              </span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--foreground-secondary)", lineHeight: 1.6, maxWidth: "28ch" }}>
              AI-powered travel planning for India. Free, fast, and grounded in real places.
            </p>
          </div>

          {/* Plan */}
          <div>
            <h4 style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--foreground)", marginBottom: "0.75rem" }}>Plan</h4>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <li><a href="#plan" style={{ fontSize: "0.85rem", color: "var(--foreground-secondary)", textDecoration: "none" }}>Plan a trip</a></li>
              <li><a href="#features" style={{ fontSize: "0.85rem", color: "var(--foreground-secondary)", textDecoration: "none" }}>How it works</a></li>
              <li><a href="#destinations" style={{ fontSize: "0.85rem", color: "var(--foreground-secondary)", textDecoration: "none" }}>Destinations</a></li>
            </ul>
          </div>

          {/* Destinations */}
          <div>
            <h4 style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--foreground)", marginBottom: "0.75rem" }}>Destinations</h4>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {["Goa", "Jaipur", "Manali", "Kerala"].map((city) => (
                <li key={city}>
                  <a href="#destinations" style={{ fontSize: "0.85rem", color: "var(--foreground-secondary)", textDecoration: "none" }}>{city}</a>
                </li>
              ))}
            </ul>
          </div>

          {/* About */}
          <div>
            <h4 style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--foreground)", marginBottom: "0.75rem" }}>About</h4>
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <li>
                <a
                  href="https://github.com/Bilal-03/ai-travel-planner-india"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: "0.85rem", color: "var(--foreground-secondary)", textDecoration: "none" }}
                >
                  GitHub
                </a>
              </li>
              <li><span style={{ fontSize: "0.85rem", color: "var(--foreground-secondary)" }}>MIT License</span></li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div
          style={{
            marginTop: "2.5rem",
            paddingTop: "1.25rem",
            borderTop: "1px solid rgba(0,0,0,0.08)",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "0.75rem",
          }}
        >
          <span style={{ fontSize: "0.78rem", color: "var(--foreground-muted)" }}>
            © 2026 YatraAI · Built with 💜 in India
          </span>
          <span style={{ fontSize: "0.78rem", color: "var(--foreground-muted)" }}>
            100% free-tier powered · No credit card needed
          </span>
        </div>
      </div>

      <style jsx>{`
        @media (max-width: 768px) {
          .footer-grid {
            grid-template-columns: 1fr 1fr !important;
          }
        }
        @media (max-width: 480px) {
          .footer-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </footer>
  );
}
