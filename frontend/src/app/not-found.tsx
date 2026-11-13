import Link from "next/link";
import { Button } from "@/components/ui/button";
export default function NotFound() {
  return (
    <section className="empty-state">
      <p className="eyebrow">404 / OUTSIDE THE PERIMETER</p>
      <h1>Page not found.</h1>
      <p>Return to your intelligence workspace.</p>
      <Button asChild>
        <Link href="/">Back to overview</Link>
      </Button>
    </section>
  );
}
