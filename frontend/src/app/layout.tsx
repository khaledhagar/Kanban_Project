import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Fonts are self-hosted (not fetched from Google at build/dev time) so the
// build, dev server, and e2e tests do not depend on network access.
const displayFont = localFont({
  src: "./fonts/SpaceGrotesk-latin.woff2",
  variable: "--font-display",
  weight: "300 700",
  display: "swap",
});

const bodyFont = localFont({
  src: "./fonts/Manrope-latin.woff2",
  variable: "--font-body",
  weight: "200 800",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Kanban Studio",
  description: "A focused, single-board kanban workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${displayFont.variable} ${bodyFont.variable}`}>
        {children}
      </body>
    </html>
  );
}
