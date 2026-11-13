import Link from "next/link";
import { ArrowUpRight, FileText } from "lucide-react";
import { documents } from "@/lib/documents";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
export function DocumentCard({
  document,
  compact = false,
}: {
  document: (typeof documents)[number];
  compact?: boolean;
}) {
  return (
    <article
      className={`document-card ${document.color} ${compact ? "compact" : ""}`}
    >
      <div className="document-top">
        <div className="document-cover" aria-hidden="true">
          <span>{document.short}</span>
          <FileText size={26} strokeWidth={1} />
          <div className="cover-lines">
            <i />
            <i />
            <i />
          </div>
        </div>
        <Badge>{document.kind}</Badge>
      </div>
      <div className="document-body">
        <p className="document-subtitle">{document.subtitle}</p>
        <h3>{document.title}</h3>
        <p>{document.description}</p>
      </div>
      <div className="document-footer">
        <span>
          {document.pages} pages<span className="dot-separator">·</span>
          {document.chunks} chunks
        </span>
        <Button asChild size="icon" variant="ghost">
          <Link
            href={`/assistant?q=${encodeURIComponent(document.question)}`}
            aria-label={`Ask about ${document.title}`}
          >
            <ArrowUpRight size={18} />
          </Link>
        </Button>
      </div>
      {!compact && (
        <div className="document-filename">
          <span>PDF citation filename</span>
          <code>{document.filename}</code>
        </div>
      )}
    </article>
  );
}
