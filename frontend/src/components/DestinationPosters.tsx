const DESTINATIONS = [
  ["GOA", "COASTAL ESCAPE", "☀"], ["HAMPI", "STONE & STORIES", "◒"], ["RISHIKESH", "RIVER & RIDGES", "〰"],
  ["MANALI", "MOUNTAIN AIR", "▲"], ["JAIPUR", "PINK CITY", "✦"], ["KERALA", "SLOW WATERS", "⌇"],
];

export default function DestinationPosters() {
  return <section className="mx-auto max-w-6xl px-4 pb-24">
    <p className="section-eyebrow">Collect stories, not tabs</p>
    <h2 className="font-display mt-2 text-4xl text-foreground md:text-5xl">Start with a destination</h2>
    <div className="mt-8 grid grid-cols-2 gap-3 md:grid-cols-3">
      {DESTINATIONS.map(([name, caption, glyph], index) => <article key={name} className="poster-card rounded-sm p-5" style={{ filter: index % 2 ? "hue-rotate(16deg)" : undefined }}>
        <span className="font-ticket text-[10px] tracking-[.18em] text-[#0b1330]">YATRAAI / INDIA</span>
        <div className="relative z-10 mt-10"><h3 className="font-display text-5xl text-[#0b1330] md:text-6xl">{name}</h3><p className="font-ticket text-[10px] tracking-[.12em] text-[#0b1330]">{caption}</p></div>
        <span className="absolute bottom-3 right-5 z-10 text-6xl text-[#f4eede]">{glyph}</span>
      </article>)}
    </div>
  </section>;
}
