import type { Metadata } from "next";
import { Outfit, Source_Serif_4 } from "next/font/google";

import { messages } from "@/i18n/pt-BR";

import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
});

export const metadata: Metadata = {
  title: messages.appName,
  description: messages.appTagline,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className={`${outfit.variable} ${sourceSerif.variable}`}>
        {children}
      </body>
    </html>
  );
}
