import { FileText, Quote, ArrowDownRight } from "lucide-react";
import type { AnswerCitation } from "@/lib/api-types";
export function CitationList({ citations }: { citations: AnswerCitation[] }) {
  if (!citations.length) return null;
  return (
    <section className="citation-section" aria-label="Source citations">
      <h3>
        <Quote size={13} />
        SOURCE EVIDENCE <span>{citations.length}</span>
      </h3>
      <div className="citation-list">
        {citations.map((c, index) => (
          <details key={`${c.evidence_id}-${index}`} className="citation-card">
            <summary>
              <span className="citation-number">
                {String(index + 1).padStart(2, "0")}
              </span>
              <FileText size={15} />
              <span>
                <strong>{c.display_title}</strong>
                <small>
                  PDF page {c.page_number} · Chunk {c.chunk_index}
                  {c.source_kind === "synthetic_incident"
                    ? " · Synthetic example"
                    : ""}
                </small>
              </span>
              <ArrowDownRight size={15} />
            </summary>
            <div className="citation-detail">
              <blockquote>{c.quote}</blockquote>
              <code>{c.filename}</code>
              <span>Evidence ID: {c.evidence_id}</span>
              <p>
                Source provenance does not by itself prove completeness or
                factual entailment.
              </p>
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
