export default function Footer() {
  return (
    <footer className="border-t border-glass-border">
      <div className="max-w-6xl mx-auto px-4 py-10 flex flex-wrap items-center justify-between gap-5">
        <span className="font-[family-name:var(--font-teko)] font-semibold uppercase text-xl tracking-wide text-foreground">
          Yatra<span className="text-marigold">AI</span>
        </span>

        <div className="flex items-center gap-6 font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted">
          <a href="#trip-form" className="hover:text-marigold transition-colors">
            Plan a trip
          </a>
          <a href="#destinations" className="hover:text-marigold transition-colors">
            Destinations
          </a>
          <a
            href="https://github.com/Bilal-03/ai-travel-planner-india"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-marigold transition-colors"
          >
            GitHub
          </a>
        </div>

        <span className="font-[family-name:var(--font-space-mono)] text-[10px] text-foreground-muted tracking-wide">
          Gemini AI · OpenStreetMap · Amadeus · OpenWeatherMap
        </span>
      </div>
      <div className="text-center pb-6 font-[family-name:var(--font-space-mono)] text-[10px] text-foreground-muted/70 tracking-wide">
        Entirely free-tier powered — no credit card needed
      </div>
    </footer>
  );
}
