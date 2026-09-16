import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SmartDNS Console Gaming Platform",
  description: "Low Latency SmartDNS & Anti-Sanction for PlayStation 5, Xbox, & PC",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0d14] text-gray-100 antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
