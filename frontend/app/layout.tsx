import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RateMyRental — Dallas Landlord Transparency",
  description: "Look up any Dallas rental property — owner info, eviction history, tenant reviews, and AI risk reports. All free, all public data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-950 text-gray-100 antialiased">
        {children}
      </body>
    </html>
  );
}
