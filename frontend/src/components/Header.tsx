"use client";

interface HeaderProps {
  onLogoClick?: () => void;
}

export default function Header({ onLogoClick }: HeaderProps) {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-background/75 border-b border-glass-border">
      <div className="max-w-[1180px] mx-auto flex items-center justify-between px-7 py-4">
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

        <nav>
          <a
            href="#plan"
            className="font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-[0.08em] px-[18px] py-[10px] rounded-[3px] border border-white/25 text-foreground hover:border-marigold hover:text-marigold transition-colors"
          >
            Plan a trip
          </a>
        </nav>
      </div>
    </header>
  );
}
