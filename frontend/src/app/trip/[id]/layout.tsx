import type { Metadata } from "next";

type LayoutProps = Readonly<{ children: React.ReactNode; params: Promise<{ id: string }> }>;

export async function generateMetadata({ params }: LayoutProps): Promise<Metadata> {
  const { id } = await params;
  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  if (!apiBase) return { title: "Shared India Itinerary | YatraAI" };

  try {
    const response = await fetch(`${apiBase}/api/trips/${id}`, { next: { revalidate: 3600 } });
    if (!response.ok) throw new Error("Trip not found");
    const trip = await response.json();
    const title = `${trip.total_days}-day ${trip.destination.name} itinerary from ${trip.origin.name} | YatraAI`;
    const description = `A ${trip.total_days}-day ${trip.destination.name} trip plan with a ₹${trip.budget.total_estimated.toLocaleString("en-IN")} estimated budget, transport, food, and activities.`;
    return { title, description, openGraph: { title, description, type: "article" } };
  } catch {
    return { title: "Shared India Itinerary | YatraAI" };
  }
}

export default function SharedTripLayout({ children }: LayoutProps) {
  return children;
}
