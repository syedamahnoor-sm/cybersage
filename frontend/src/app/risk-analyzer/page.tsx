import type { Metadata } from "next";
import { RiskWorkspace } from "@/components/risk-workspace";
export const metadata: Metadata = { title: "Risk Analyzer" };
export default function RiskPage() {
  return <RiskWorkspace />;
}
