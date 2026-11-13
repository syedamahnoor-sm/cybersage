import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Layers3,
  FileText,
  Sparkles,
  ChartNoAxesCombined,
  ShieldCheck,
  Network,
  Quote,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { KnowledgeOrbit } from "@/components/knowledge-orbit";
import { DocumentCard } from "@/components/document-card";
import { documents } from "@/lib/documents";
import { Reveal } from "@/components/reveal";

export default function Overview() {
  return (
    <div className="overview-page">
      <section className="overview-hero">
        <div className="hero-copy">
          <p className="eyebrow">
            <span /> YOUR CYBERSECURITY INTELLIGENCE WORKSPACE
          </p>
          <h1>
            Clarity in a complex
            <br />
            <span>threat landscape.</span>
          </h1>
          <p>
            Turn trusted knowledge into informed decisions.
            <br className="desktop-break" /> Explore evidence, understand risk,
            and keep the source in sight.
          </p>
          <div className="hero-actions">
            <Button asChild>
              <Link href="/assistant">
                <Sparkles size={16} />
                Open AI Assistant
                <ArrowRight size={16} />
              </Link>
            </Button>
            <Button asChild variant="ghost">
              <Link href="/about">
                Explore CyberSage
                <ArrowUpRight size={15} />
              </Link>
            </Button>
          </div>
          <div className="hero-proof">
            <ShieldCheck size={14} />
            <span>Source-grounded answers. Transparent reasoning.</span>
          </div>
        </div>
        <KnowledgeOrbit />
      </section>
      <Reveal className="corpus-strip" delay={0.05}>
        <div className="corpus-label">
          <span className="tiny-label">THE KNOWLEDGE FOUNDATION</span>
          <p>A focused, curated corpus.</p>
        </div>
        <div className="corpus-stat">
          <BookOpen size={19} />
          <div>
            <strong>03</strong>
            <span>Source documents</span>
          </div>
        </div>
        <div className="corpus-stat">
          <Layers3 size={19} />
          <div>
            <strong>206</strong>
            <span>Indexed passages</span>
          </div>
        </div>
        <div className="corpus-stat">
          <FileText size={19} />
          <div>
            <strong>75</strong>
            <span>PDF pages</span>
          </div>
        </div>
        <span className="snapshot-label">
          Verified corpus snapshot
          <br />
          Milestone 9 · Not live telemetry
        </span>
      </Reveal>
      <div className="section-heading">
        <div>
          <p className="eyebrow">FROM QUESTIONS TO UNDERSTANDING</p>
          <h2>Choose your next move.</h2>
        </div>
        <Badge>Two capabilities. One workspace.</Badge>
      </div>
      <div className="action-grid">
        <Link href="/assistant" className="action-card assistant-action">
          <div className="action-icon">
            <Sparkles size={23} />
          </div>
          <div>
            <span className="tiny-label">01 / INTELLIGENCE</span>
            <h3>Ask. Explore. Verify.</h3>
            <p>
              Get cybersecurity answers grounded in your documents, with
              page-level citations you can inspect.
            </p>
            <span className="text-link">
              Start a conversation
              <ArrowRight size={16} />
            </span>
          </div>
          <ArrowUpRight className="card-corner" size={22} />
          <div className="action-watermark" aria-hidden="true">
            ✳
          </div>
        </Link>
        <Link href="/risk-analyzer" className="action-card">
          <div className="action-icon risk-icon">
            <ChartNoAxesCombined size={23} />
          </div>
          <div>
            <span className="tiny-label">02 / ASSESSMENT</span>
            <h3>Make risk tangible.</h3>
            <p>
              Explore likelihood and impact with a transparent, deterministic 5
              × 5 risk matrix.
            </p>
            <span className="text-link">
              Analyze a scenario
              <ArrowRight size={16} />
            </span>
          </div>
          <ArrowUpRight className="card-corner" size={22} />
        </Link>
      </div>
      <div className="section-heading">
        <div>
          <p className="eyebrow">BUILT ON TRUSTED CONTEXT</p>
          <h2>Your knowledge, connected.</h2>
        </div>
        <Link href="/knowledge-base" className="text-link subtle-link">
          Explore knowledge base
          <ArrowRight size={16} />
        </Link>
      </div>
      <div className="document-grid">
        {documents.map((document) => (
          <DocumentCard key={document.id} document={document} compact />
        ))}
      </div>
      <section className="principles-strip" aria-label="Capabilities">
        <div>
          <Quote size={18} />
          <span>
            <strong>Evidence, not guesswork.</strong>
            <small>Inspect the passages behind each answer.</small>
          </span>
        </div>
        <div>
          <Network size={18} />
          <span>
            <strong>Context that stays with you.</strong>
            <small>Conversation-scoped, persistent memory.</small>
          </span>
        </div>
        <div>
          <ShieldCheck size={18} />
          <span>
            <strong>Built to know its limits.</strong>
            <small>Explicit abstention when evidence falls short.</small>
          </span>
        </div>
      </section>
    </div>
  );
}
