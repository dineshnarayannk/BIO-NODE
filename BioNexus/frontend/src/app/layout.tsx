import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

export const metadata: Metadata = {
  title: "BioNexus | Connecting Natural Compounds to Biological Insights",
  description:
    "An evidence-driven biological knowledge discovery platform that helps users explore relationships between natural compounds, proteins, genes, pathways, and biological processes.",
  keywords: [
    "BioNexus",
    "Natural Compounds",
    "Bioactivity",
    "Knowledge Graph",
    "StreptomeDB",
    "Pharmacology",
    "Pathways",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${outfit.variable} dark`}>
      <body className="flex flex-col min-h-screen bg-slate-950 text-slate-100">
        {children}
      </body>
    </html>
  );
}
