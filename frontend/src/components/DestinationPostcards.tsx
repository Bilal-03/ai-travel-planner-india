"use client";

import { motion } from "framer-motion";
import {
  GoaArt,
  HampiArt,
  RishikeshArt,
  ManaliArt,
  JaipurArt,
  KeralaArt,
  VaranasiArt,
  MumbaiArt,
} from "./PostcardArt";

interface Destination {
  city: string;
  meta: string;
  Art: React.ComponentType;
}

const DESTINATIONS: Destination[] = [
  { city: "Goa", meta: "Beaches & sunsets", Art: GoaArt },
  { city: "Hampi", meta: "Ancient ruins", Art: HampiArt },
  { city: "Rishikesh", meta: "River & hills", Art: RishikeshArt },
  { city: "Manali", meta: "Mountain escapes", Art: ManaliArt },
  { city: "Jaipur", meta: "Forts & jaali", Art: JaipurArt },
  { city: "Kerala", meta: "Backwaters & coasts", Art: KeralaArt },
  { city: "Varanasi", meta: "Ghats & temples", Art: VaranasiArt },
  { city: "Mumbai", meta: "Coast & culture", Art: MumbaiArt },
];

export default function DestinationPostcards() {
  return (
    <section id="destinations" className="px-7 pt-[10px] pb-[110px]">
      <div className="max-w-[1180px] mx-auto">
        <div className="flex flex-wrap items-end justify-between gap-5 mb-10">
          <div>
            <span className="font-[family-name:var(--font-space-mono)] text-xs uppercase tracking-[0.16em] text-marigold">
              Where people are heading
            </span>
            <h2 className="mt-3 font-[family-name:var(--font-teko)] font-semibold uppercase tracking-wide text-3xl md:text-4xl text-foreground">
              Eight starting points
            </h2>
          </div>
          <p className="text-foreground-muted max-w-sm">
            From backwaters to high passes — a sense of the range YatraAI plans for.
          </p>
        </div>

        <div className="grid grid-cols-[repeat(auto-fill,minmax(230px,1fr))] gap-[22px]">
          {DESTINATIONS.map((d, idx) => (
            <motion.article
              key={d.city}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ delay: idx * 0.05, duration: 0.5 }}
              whileHover={{ y: -6 }}
              className="relative rounded-lg overflow-hidden bg-cream shadow-[0_24px_50px_-22px_rgba(0,0,0,0.55)]"
            >
              <span className="postcard-hole absolute top-3.5 left-3.5 z-10 w-3.5 h-3.5 rounded-full bg-[#0B1330]" />
              <d.Art />
              <div className="px-4 pt-3 pb-4 bg-cream">
                <div className="font-[family-name:var(--font-teko)] font-semibold uppercase tracking-wide text-2xl leading-none text-[#24160a]">
                  {d.city}
                </div>
                <div className="mt-1.5 font-[family-name:var(--font-space-mono)] text-[10px] uppercase tracking-wide text-[#6b4a30]">
                  {d.meta}
                </div>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
