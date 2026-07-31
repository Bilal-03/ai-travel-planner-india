"use client";

interface HeaderProps {
  onLogoClick?: () => void;
}

export default function Header({ onLogoClick }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-background/75 border-b border-glass-border">
      <div className="max-w-6xl mx-auto flex items-center justify-between px-4 py-4">
        <button
          onClick={onLogoClick}
          type="button"
          className="flex items-baseline gap-2.5"
        >
          <span className="font-[family-name:var(--font-teko)] font-semibold uppercase text-2xl tracking-wide text-foreground">
            Yatra<span className="text-marigold">AI</span>
          </span>
          <span className="hidden sm:inline font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-[0.14em] text-foreground-muted">
            Ghoomte raho
          </span>
        </button>

        <nav className="flex items-center gap-5 sm:gap-6">
          <a
            href="#trip-form"
            className="hidden sm:inline font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted hover:text-foreground transition-colors"
          >
            Plan a trip
          </a>
          <a
            href="#destinations"
            className="hidden sm:inline font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide text-foreground-muted hover:text-foreground transition-colors"
          >
            Destinations
          </a>
          <a
            href="#trip-form"
            className="font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-wide px-4 py-2.5 rounded-[3px] border border-glass-border text-foreground hover:border-marigold hover:text-marigold transition-colors"
          >
            Plan my journey
          </a>
        </nav>
      </div>
    </header>
  );
}
