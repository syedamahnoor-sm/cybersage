import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Database,
  GitBranch,
  Layers3,
  MessageSquare,
  Quote,
  ShieldCheck,
  Sparkles,
  Calculator,
  LockKeyhole,
} from "lucide-react";
import { PageIntro } from "@/components/page-intro";
import { BrandMark } from "@/components/brand";
import { Button } from "@/components/ui/button";
export const metadata: Metadata = { title: "About" };
const steps = [
  {
    icon: MessageSquare,
    title: "Your question",
    detail:
      "Bounded conversational context resolves follow-ups before fresh retrieval.",
  },
  {
    icon: GitBranch,
    title: "LangGraph agent",
    detail:
      "A bounded, single-agent graph selects knowledge retrieval or deterministic risk scoring.",
  },
  {
    icon: Database,
    title: "pgvector retrieval",
    detail:
      "Normalized MiniLM embeddings find relevant passages using cosine distance.",
  },
  {
    icon: Sparkles,
    title: "Grounded generation",
    detail:
      "Groq generates source-constrained excerpts. Validation can reject unsupported answers.",
  },
  {
    icon: Quote,
    title: "Cited response",
    detail:
      "Evidence IDs map back to actual document metadata and physical PDF pages.",
  },
];
export default function AboutPage() {
  return (
    <>
      <PageIntro
        eyebrow="ABOUT / ENGINEERED FOR UNDERSTANDING"
        title="Intelligence with a paper trail."
        description="CyberSage connects cybersecurity questions to a focused knowledge base—keeping evidence, uncertainty, and context visible."
      />
      <section className="about-hero card">
        <div className="about-brand">
          <BrandMark />
        </div>
        <div>
          <p className="eyebrow">THE CYBERSAGE PRINCIPLE</p>
          <h2>
            Confidence begins
            <br />
            with knowing the source.
          </h2>
          <p>
            A research platform for exploring policy, framework guidance and
            synthetic security scenarios. CyberSage combines retrieval-augmented
            generation with explicit citation checks and a transparent risk
            tool.
          </p>
          <Button asChild variant="outline">
            <Link href="/assistant">
              Explore the assistant
              <ArrowRight size={15} />
            </Link>
          </Button>
        </div>
      </section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">THE ARCHITECTURE</p>
          <h2>From question to evidence.</h2>
        </div>
        <span className="muted">One bounded agent. Two capabilities.</span>
      </div>
      <section className="architecture" aria-label="RAG architecture">
        <ol>
          {steps.map(({ icon: Icon, title, detail }, index) => (
            <li key={title}>
              <div className="architecture-top">
                <span>0{index + 1}</span>
                <Icon size={20} />
              </div>
              <h3>{title}</h3>
              <p>{detail}</p>
              {index < steps.length - 1 && (
                <ArrowRight
                  className="architecture-arrow"
                  size={16}
                  aria-hidden="true"
                />
              )}
            </li>
          ))}
        </ol>
        <div className="architecture-branch">
          <Calculator size={18} />
          <strong>Risk branch</strong>
          <span>Likelihood × impact → validated 1–25 score → category</span>
          <span className="badge">No LLM arithmetic</span>
        </div>
      </section>
      <div className="about-features">
        {[
          {
            icon: BookOpen,
            title: "A curated knowledge layer",
            text: "Three PDFs span Pakistan’s 2021 national policy, NIST CSF 2.0, and a clearly labeled synthetic incident casebook.",
          },
          {
            icon: Layers3,
            title: "Context with boundaries",
            text: "PostgreSQL persists conversation-scoped messages. Recent user context resolves follow-ups; prior assistant answers are not factual evidence.",
          },
          {
            icon: ShieldCheck,
            title: "Grounding over persuasion",
            text: "Source IDs, page metadata and exact quote checks protect citation provenance. When support is insufficient, CyberSage abstains.",
          },
          {
            icon: LockKeyhole,
            title: "Transparent limitations",
            text: "This local research workspace has no authentication. Conversation IDs grant history access. Avoid sensitive data; citations do not guarantee completeness.",
          },
        ].map(({ icon: Icon, title, text }) => (
          <article className="card" key={title}>
            <Icon size={22} />
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </div>
      <div className="technology-strip">
        <span>BUILT WITH</span>
        {[
          "FastAPI",
          "PostgreSQL + pgvector",
          "MiniLM · 384 dimensions",
          "Groq · gpt-oss-120b",
          "LangGraph",
          "Next.js",
        ].map((t) => (
          <span key={t}>{t}</span>
        ))}
      </div>
    </>
  );
}
