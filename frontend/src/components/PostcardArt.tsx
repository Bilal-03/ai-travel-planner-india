// Flat, mid-century Indian Railways travel-poster style illustrations.
// Kept as simple geometric SVG (not photos) so the whole gallery reads
// as one consistent illustrated set rather than mismatched stock photography.

export function GoaArt() {
  return (
    <svg className="w-full aspect-[4/3] block" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="300" fill="#F2A93B" />
      <rect y="190" width="400" height="110" fill="#1C8079" />
      <circle cx="300" cy="150" r="60" fill="#C4522B" />
      <path d="M0 210 Q 100 180 200 210 T 400 210 V300 H0 Z" fill="#166b65" />
      <path d="M60 190 L60 110 Q 90 100 100 130 Q 60 130 60 190" fill="#0B1330" />
      <path d="M60 130 L20 150 M60 140 L15 175 M60 150 L20 195" stroke="#0B1330" strokeWidth="5" fill="none" />
    </svg>
  );
}

export function HampiArt() {
  return (
    <svg className="w-full aspect-[4/3] block" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="300" fill="#E8901F" />
      <rect y="220" width="400" height="80" fill="#C4522B" />
      <circle cx="90" cy="70" r="42" fill="#F4EEDE" opacity="0.85" />
      <ellipse cx="150" cy="230" rx="70" ry="46" fill="#8a3e22" />
      <ellipse cx="260" cy="220" rx="55" ry="60" fill="#7a3620" />
      <ellipse cx="330" cy="235" rx="40" ry="35" fill="#93482a" />
      <rect x="220" y="150" width="18" height="70" fill="#0B1330" />
      <polygon points="229,120 245,150 213,150" fill="#0B1330" />
    </svg>
  );
}

export function RishikeshArt() {
  return (
    <svg className="w-full aspect-[4/3] block" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="300" fill="#1C8079" />
      <polygon points="0,180 120,60 240,180" fill="#155f5a" />
      <polygon points="150,180 260,40 400,180" fill="#0e4642" />
      <rect y="180" width="400" height="120" fill="#2fa79d" />
      <path d="M0 200 Q200 170 400 205 V300 H0 Z" fill="#F4EEDE" opacity="0.9" />
      <line x1="40" y1="185" x2="360" y2="185" stroke="#C4522B" strokeWidth="6" />
      <line x1="40" y1="185" x2="40" y2="150" stroke="#C4522B" strokeWidth="4" />
      <line x1="360" y1="185" x2="360" y2="150" stroke="#C4522B" strokeWidth="4" />
    </svg>
  );
}

export function ManaliArt() {
  return (
    <svg className="w-full aspect-[4/3] block" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="300" fill="#0B1330" />
      <polygon points="0,190 90,70 180,190" fill="#3a4590" />
      <polygon points="120,190 230,40 340,190" fill="#525fb0" />
      <polygon points="260,190 340,90 400,190" fill="#3a4590" />
      <polygon points="90,70 100,90 80,90" fill="#F4EEDE" />
      <polygon points="230,40 244,66 216,66" fill="#F4EEDE" />
      <polygon points="340,90 350,108 330,108" fill="#F4EEDE" />
      <rect y="190" width="400" height="110" fill="#141b44" />
      <polygon points="30,300 55,230 80,300" fill="#0e1230" />
      <polygon points="90,300 115,220 140,300" fill="#0e1230" />
    </svg>
  );
}

export function JaipurArt() {
  return (
    <svg className="w-full aspect-[4/3] block" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="300" fill="#C4522B" />
      <rect y="140" width="400" height="160" fill="#a83f1e" />
      <rect x="70" y="70" width="260" height="140" fill="#F2A93B" />
      <g fill="#a83f1e">
        <circle cx="100" cy="100" r="9" /><circle cx="140" cy="100" r="9" /><circle cx="180" cy="100" r="9" />
        <circle cx="220" cy="100" r="9" /><circle cx="260" cy="100" r="9" /><circle cx="300" cy="100" r="9" />
        <circle cx="100" cy="140" r="9" /><circle cx="140" cy="140" r="9" /><circle cx="180" cy="140" r="9" />
        <circle cx="220" cy="140" r="9" /><circle cx="260" cy="140" r="9" /><circle cx="300" cy="140" r="9" />
        <circle cx="100" cy="180" r="9" /><circle cx="140" cy="180" r="9" /><circle cx="180" cy="180" r="9" />
        <circle cx="220" cy="180" r="9" /><circle cx="260" cy="180" r="9" /><circle cx="300" cy="180" r="9" />
      </g>
      <rect x="70" y="70" width="260" height="14" fill="#a83f1e" />
    </svg>
  );
}

export function KeralaArt() {
  return (
    <svg className="w-full aspect-[4/3] block" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice">
      <rect width="400" height="300" fill="#166b65" />
      <rect y="200" width="400" height="100" fill="#0e4642" />
      <path d="M0 200 Q200 170 400 200 V300 H0 Z" fill="#1C8079" />
      <rect x="120" y="150" width="160" height="55" rx="6" fill="#F4EEDE" />
      <rect x="140" y="120" width="120" height="35" rx="16" fill="#e0d6b8" />
      <rect x="115" y="200" width="170" height="14" fill="#a83f1e" />
      <ellipse cx="60" cy="90" rx="16" ry="16" fill="#F2A93B" />
      <path d="M60 90 Q40 60 60 30 Q80 60 60 90" fill="#0e4642" />
    </svg>
  );
}
