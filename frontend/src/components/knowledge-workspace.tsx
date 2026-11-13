"use client";
import { useState } from "react";
import { Search, BookOpen, Info, X } from "lucide-react";
import { PageIntro } from "./page-intro";
import { DocumentCard } from "./document-card";
import { documents } from "@/lib/documents";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
export function KnowledgeWorkspace() {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("All sources");
  const filtered = documents.filter(
    (d) =>
      (filter === "All sources" || d.kind === filter) &&
      `${d.title} ${d.subtitle} ${d.description} ${d.kind}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <>
      <PageIntro
        eyebrow="KNOWLEDGE / THE SOURCE OF YOUR ANSWERS"
        title="A foundation you can inspect."
        description="Three curated documents. Policy, framework guidance, and synthetic scenarios—clearly distinguished."
        action={
          <Badge>
            <BookOpen size={12} />3 source documents
          </Badge>
        }
      />
      <div className="knowledge-summary">
        <div>
          <strong>03</strong>
          <span>Curated sources</span>
        </div>
        <div>
          <strong>75</strong>
          <span>PDF pages</span>
        </div>
        <div>
          <strong>206</strong>
          <span>Indexed passages</span>
        </div>
        <p>
          Verified corpus snapshot from Milestone 9.
          <br />
          This catalog is not a live database inventory.
        </p>
      </div>
      <div className="knowledge-toolbar">
        <div className="search-field">
          <Search size={17} />
          <input
            aria-label="Filter source documents"
            placeholder="Find a source, topic, or framework…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <Button
              size="icon"
              variant="ghost"
              aria-label="Clear search"
              onClick={() => setQuery("")}
            >
              <X size={14} />
            </Button>
          )}
        </div>
        <label className="source-filter">
          Source type
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            {["All sources", ...documents.map((d) => d.kind)].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="result-count" role="status">
        {filtered.length} of 3 sources
      </p>
      <div className="document-grid knowledge-documents">
        {filtered.map((document) => (
          <DocumentCard document={document} key={document.id} />
        ))}
      </div>
      {!filtered.length && (
        <div className="empty-state">
          <Search size={28} />
          <h2>No matching sources.</h2>
          <p>Try a different topic or source type.</p>
          <Button
            variant="outline"
            onClick={() => {
              setQuery("");
              setFilter("All sources");
            }}
          >
            Clear filters
          </Button>
        </div>
      )}
      <div className="info-panel">
        <Info size={19} />
        <div>
          <h2>Every source has a role.</h2>
          <p>
            Policy requirements, framework guidance, and fictional incident
            examples are different kinds of evidence. CyberSage preserves that
            distinction in its answers and citations. The casebook is synthetic
            and must not be interpreted as a record of real events.
          </p>
          <p>
            Inspect source excerpts in assistant citations. PDF viewing,
            downloads, uploads and document management are not available in this
            interface.
          </p>
        </div>
      </div>
    </>
  );
}
