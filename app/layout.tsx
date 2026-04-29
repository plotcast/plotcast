import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rendara — Automated Data-to-Video Production",
  description:
    "Turn your CSV and spreadsheet data into polished branded videos, automatically. Upload your data, receive a professional video in 48 hours.",
  openGraph: {
    title: "Rendara — Automated Data-to-Video Production",
    description:
      "Send us your CSV or spreadsheet. We return a polished, branded video in 48 hours.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col antialiased">
        {children}
        <Script
          src="https://phospho-nanocorp-prod--nanocorp-api-fastapi-app.modal.run/beacon/snippet.js?s=rendara"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
