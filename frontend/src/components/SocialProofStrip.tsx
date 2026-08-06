"use client";

export default function SocialProofStrip() {
  const items = [
    { icon: "✦", text: "No sign-up needed" },
    { icon: "✦", text: "Free to plan" },
    { icon: "✦", text: "Built for India" },
    { icon: "✦", text: "Powered by Gemini" },
  ];

  return (
    <div className="trust-strip">
      {items.map((item, idx) => (
        <div key={idx} className="trust-strip-item">
          <span style={{ color: "var(--marigold)" }}>{item.icon}</span>
          <span>{item.text}</span>
        </div>
      ))}
    </div>
  );
}
