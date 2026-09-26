import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";
import GravitationalField from "@/components/GravitationalField";

const fontSansClass = "font-sans";
const fontMonoClass = "font-mono";

export const metadata: Metadata = {
  title: "ReFind — Find what you remember.",
  description: "A privacy-focused, context-aware digital memory search system developed by BitByBit.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full antialiased">
      <body className="min-h-full flex flex-col bg-black text-zinc-100 font-sans selection:bg-indigo-500/25 selection:text-indigo-200 relative overflow-x-hidden text-base">
        {/* Deep space gravitational distortion particle canvas */}
        <GravitationalField />

        {/* Ambient space-time perimeter vignette */}
        <div className="fixed inset-0 gravitational-vignette z-[1] pointer-events-none" />

        {/* UI Content Layer above particle canvas */}
        <div className="relative z-10 flex-1 flex flex-col">
          <Navbar />
          <main className="flex-1 flex flex-col">{children}</main>
          <footer className="border-t border-white/[0.08] bg-black/40 backdrop-blur-md py-6 text-center text-sm text-zinc-400 font-mono">
            <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
              <span className="tracking-wide">ReFind · Find what you remember</span>
              <span>Built by <strong className="text-zinc-200 font-medium tracking-wider">BitByBit</strong></span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
