import type { Metadata } from "next";
import { Inter, Manrope, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "IVEN-TRON | Autonomous Smart Warehouse System",
  description: "A compact, low-cost autonomous robotic system for smart inventory handling and predictive warehouse management in SMEs. An engineering design project by DFP-38 team at PDPM IIITDM Jabalpur.",
  keywords: ["autonomous warehouse", "smart inventory", "robotics", "IoT", "machine learning", "SME automation", "IVEN-TRON"],
  authors: [{ name: "DFP-38 Team" }],
  openGraph: {
    title: "IVEN-TRON | Autonomous Smart Warehouse System",
    description: "A compact, low-cost autonomous robotic system for smart inventory handling and predictive warehouse management in SMEs.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${manrope.variable} ${jetbrainsMono.variable} antialiased bg-black text-white`}
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
