export default function Footer() {
  return (
    <footer className="border-t border-glass-border">
      <div className="max-w-[1180px] mx-auto px-7 py-10 flex flex-wrap items-center justify-between gap-4">
        <span className="font-[family-name:var(--font-teko)] font-semibold uppercase text-xl tracking-wide text-foreground">
          Yatra<span className="text-marigold">AI</span>
        </span>

        <div className="flex items-center gap-6 font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted">
          <a href="#plan" className="hover:text-marigold transition-colors">
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

        <span className="font-[family-name:var(--font-space-mono)] text-[0.68rem] text-foreground-muted tracking-[0.05em]">Built for the next Indian trip · 100% free-tier</span>
      </div>
    </footer>
  );
}
