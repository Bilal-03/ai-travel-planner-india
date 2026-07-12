import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "YatraAI — AI-Powered India Travel Planner",
  description:
    "Plan your perfect domestic India trip with AI. Get personalized day-by-day itineraries, flight & train options, budget breakdowns, and weather-aware recommendations — all for free.",
  keywords: [
    "India travel planner",
    "AI itinerary",
    "domestic travel",
    "trip planner",
    "budget travel India",
  ],
  openGraph: {
    title: "YatraAI — Plan Your Perfect India Trip with AI",
    description:
      "AI-powered domestic India travel itineraries with flights, trains, weather forecasts, and budget tracking.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${outfit.variable}`}>
      <head>
        <meta name="color-scheme" content="dark" />
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `{
              const theme = localStorage.getItem("theme");
              if (theme === "light") {
                document.documentElement.setAttribute("data-theme", "light");
                document.querySelector('meta[name="color-scheme"]').content = "light";
              }
            }`,
          }}
        />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
