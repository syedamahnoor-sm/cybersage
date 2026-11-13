import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/manrope";
import "./globals.css";
import { AppShell } from "@/components/app-shell";
export const metadata: Metadata = {
  title: {
    default: "CyberSage — Intelligence Workspace",
    template: "%s | CyberSage",
  },
  description:
    "Evidence-grounded cybersecurity intelligence, verified PDF citations, and transparent risk assessment.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
