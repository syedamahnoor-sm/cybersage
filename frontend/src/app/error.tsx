"use client";
import { Button } from "@/components/ui/button";
import { ShieldAlert } from "lucide-react";
export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="empty-state">
      <ShieldAlert size={36} />
      <h1>This workspace couldn’t load.</h1>
      <p>
        Your source documents have not been changed. Try loading the page again.
      </p>
      <Button onClick={reset}>Try again</Button>
    </section>
  );
}
