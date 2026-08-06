import type { Metadata } from "next";
import { Manrope, Outfit, Playfair_Display } from "next/font/google";
import ServiceWorkerRegistrar from "@/components/ServiceWorkerRegistrar";
import "./globals.css";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  display: "swap",
});

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  display: "swap",
});

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
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
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} ${outfit.variable} ${playfair.variable}`}
    >
      <head>
        <meta name="color-scheme" content="light" />
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased">
        <ServiceWorkerRegistrar />
        {children}
      </body>
    </html>
  );
}
