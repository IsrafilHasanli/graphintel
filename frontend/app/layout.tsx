import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "GraphIntel — Support & Incident Intelligence",
  description:
    "Graph RAG platform for support tickets, incidents, postmortems, runbooks, and SLAs.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-brand focus:px-3 focus:py-1.5 focus:text-sm focus:text-white"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main" className="mx-auto min-h-[calc(100vh-57px)] max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
