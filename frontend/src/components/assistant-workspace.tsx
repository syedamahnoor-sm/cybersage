"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowUp,
  ArrowUpRight,
  BookOpen,
  Check,
  Copy,
  History,
  LoaderCircle,
  MessageSquare,
  Plus,
  RotateCcw,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  AgentRequest,
  AgentResponse,
  HistoryMessage,
} from "@/lib/api-types";
import { validateQuestion } from "@/lib/risk";
import {
  rememberConversation,
  useRecentConversations,
} from "@/lib/conversations";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Badge } from "./ui/badge";
import { BrandMark } from "./brand";
import { CitationList } from "./citation-list";
import { SafeMarkdown } from "./safe-markdown";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: AgentResponse;
}
const suggestions = [
  {
    tag: "FRAMEWORK",
    question: "How does NIST CSF 2.0 address incident response?",
  },
  {
    tag: "NATIONAL POLICY",
    question:
      "What does Pakistan's cyber security policy say about critical infrastructure?",
  },
  {
    tag: "SYNTHETIC CASEBOOK",
    question:
      "In casebook incident CS-INC-017, what happened to the backup deletion requests?",
  },
];
function historyMessage(row: HistoryMessage): Message {
  const meta = row.metadata;
  const response =
    row.role === "assistant" &&
    typeof meta.status === "string" &&
    Array.isArray(meta.citations)
      ? (meta as unknown as AgentResponse)
      : undefined;
  return {
    id: row.id,
    role: row.role === "user" ? "user" : "assistant",
    content: row.content,
    response,
  };
}
function CopyAnswer({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => () => clearTimeout(timer.current), []);
  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setFailed(false);
            timer.current = setTimeout(() => setCopied(false), 1800);
          } catch {
            setFailed(true);
          }
        }}
      >
        {copied ? <Check size={13} /> : <Copy size={13} />}
        {copied ? "Copied" : "Copy answer"}
      </Button>
      {failed && (
        <span role="status" className="muted">
          Clipboard unavailable. Select the answer to copy.
        </span>
      )}
    </>
  );
}
export function AssistantWorkspace() {
  const params = useSearchParams();
  return (
    <ChatSession
      key={`${params.get("conversation") ?? ""}/${params.get("new") ?? ""}/${params.get("q") ?? ""}`}
      initialId={params.get("conversation")}
      initialQuestion={params.get("q") ?? ""}
    />
  );
}
function ChatSession({
  initialId,
  initialQuestion,
}: {
  initialId: string | null;
  initialQuestion: string;
}) {
  const router = useRouter();
  const recent = useRecentConversations();
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState(initialQuestion.slice(0, 2000));
  const [conversation, setConversation] = useState<string | null>(initialId);
  const [pending, setPending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(Boolean(initialId));
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyVersion, setHistoryVersion] = useState(0);
  const [before, setBefore] = useState<number | null>(null);
  const [retry, setRetry] = useState<AgentRequest | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const scrollToEnd = useRef(true);
  const requestLock = useRef(false);
  const activeRequest = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  useEffect(() => () => activeRequest.current?.abort(), []);
  useEffect(() => {
    if (!initialId) return;
    const controller = new AbortController();
    async function load() {
      setLoadingHistory(true);
      setHistoryError(null);
      try {
        const data = await api.history(
          initialId!,
          undefined,
          controller.signal,
        );
        if (!controller.signal.aborted) {
          setMessages(data.messages.map(historyMessage));
          setBefore(data.has_more ? data.next_before_turn : null);
        }
      } catch (e) {
        if (!controller.signal.aborted)
          setHistoryError(
            e instanceof Error ? e.message : "History could not load.",
          );
      } finally {
        if (!controller.signal.aborted) setLoadingHistory(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [initialId, historyVersion]);
  useEffect(() => {
    if (messages.length > 0 && scrollToEnd.current)
      endRef.current?.scrollIntoView({ block: "nearest" });
    scrollToEnd.current = true;
  }, [messages, pending]);
  async function loadOlder() {
    if (!conversation || !before) return;
    setLoadingHistory(true);
    setHistoryError(null);
    const controller = new AbortController();
    activeRequest.current = controller;
    try {
      const data = await api.history(conversation, before, controller.signal);
      if (!controller.signal.aborted) {
        scrollToEnd.current = false;
        setMessages((current) => [
          ...data.messages.map(historyMessage),
          ...current,
        ]);
        setBefore(data.has_more ? data.next_before_turn : null);
      }
    } catch (e) {
      if (!controller.signal.aborted)
        setHistoryError(
          e instanceof Error ? e.message : "History could not load.",
        );
    } finally {
      if (!controller.signal.aborted) setLoadingHistory(false);
    }
  }
  async function send(existing?: AgentRequest) {
    if (requestLock.current || loadingHistory || historyError) return;
    const problem = validateQuestion(existing?.message ?? question);
    if (problem) {
      setValidation(problem);
      inputRef.current?.focus();
      return;
    }
    const payload: AgentRequest = existing ?? {
      message: question.trim(),
      top_k: 5,
      request_id: crypto.randomUUID(),
      ...(conversation ? { conversation_id: conversation } : {}),
    };
    requestLock.current = true;
    setPending(true);
    setError(null);
    setValidation(null);
    setRetry(null);
    if (!existing) {
      setMessages((current) => [
        ...current,
        { id: payload.request_id!, role: "user", content: payload.message },
      ]);
      setQuestion("");
    }
    const controller = new AbortController();
    activeRequest.current = controller;
    try {
      const response = await api.invoke(payload, controller.signal);
      if (controller.signal.aborted) return;
      if (response.status === "error")
        throw new Error(
          "The service could not complete this request. Retry when ready.",
        );
      setMessages((current) => [
        ...current,
        {
          id: `${payload.request_id}-answer`,
          role: "assistant",
          content:
            response.answer ??
            response.assessment?.interpretation ??
            response.error?.message ??
            "Please clarify your request.",
          response,
        },
      ]);
      if (response.conversation_id) {
        setConversation(response.conversation_id);
        rememberConversation(response.conversation_id, payload.message);
        if (initialId !== response.conversation_id)
          router.replace(
            `/assistant?conversation=${encodeURIComponent(response.conversation_id)}`,
            { scroll: false },
          );
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        setError(e instanceof Error ? e.message : "The request failed.");
        setRetry(payload);
      }
    } finally {
      if (!controller.signal.aborted) {
        setPending(false);
        requestLock.current = false;
        inputRef.current?.focus();
      }
    }
  }
  return (
    <div className="assistant-page">
      <div className="assistant-title">
        <div>
          <p className="eyebrow">INTELLIGENCE / SOURCE-GROUNDED</p>
          <h1>AI Assistant</h1>
        </div>
        <Badge>
          <ShieldCheck size={12} />
          Evidence comes first
        </Badge>
      </div>
      <div className="chat-layout">
        <aside className="chat-sidebar">
          <div className="chat-sidebar-header">
            <h2>Conversations</h2>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Start new assistant conversation"
              onClick={() =>
                router.push(`/assistant?new=${crypto.randomUUID()}`)
              }
            >
              <Plus size={16} />
            </Button>
          </div>
          {recent.length ? (
            recent.map((r) => (
              <Link
                href={`/assistant?conversation=${encodeURIComponent(r.id)}`}
                className={`chat-conversation ${r.id === conversation ? "selected" : ""}`}
                key={r.id}
              >
                <MessageSquare size={15} />
                <span>
                  {r.title}
                  <small>Saved conversation</small>
                </span>
              </Link>
            ))
          ) : (
            <div className="chat-no-history">
              <History size={21} />
              <p>
                A little context
                <br />
                goes a long way.
              </p>
              <small>
                Your recent conversations
                <br />
                will appear here.
              </small>
            </div>
          )}
          <div className="chat-privacy">
            <ShieldCheck size={16} />
            <p>
              Conversation IDs grant access to history. Use this local workspace
              for non-sensitive questions.
            </p>
            <small>
              Shortcuts are saved in this browser. Clearing them does not delete
              server history.
            </small>
          </div>
        </aside>
        <section className="chat-main" aria-label="Assistant conversation">
          <div className="chat-topline">
            <span>
              <span className="status-dot neutral" />
              Document-grounded mode
            </span>
            <span>
              {conversation ? "Conversation saved" : "New conversation"}
            </span>
          </div>
          <div className="chat-scroll" aria-busy={pending || loadingHistory}>
            {loadingHistory && (
              <div role="status" className="history-loading">
                <LoaderCircle size={17} className="spin" />
                Loading conversation…
              </div>
            )}
            {historyError && (
              <div className="chat-error" role="alert">
                <TriangleAlert size={18} />
                <p>{historyError}</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setHistoryVersion((v) => v + 1)}
                >
                  Retry history
                </Button>
              </div>
            )}
            {before && !loadingHistory && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void loadOlder()}
              >
                Load earlier messages
              </Button>
            )}
            {!messages.length && !loadingHistory && !historyError && (
              <div className="chat-empty">
                <div className="assistant-emblem">
                  <BrandMark />
                </div>
                <p className="eyebrow">GOOD QUESTIONS. GROUNDED ANSWERS.</p>
                <h2>
                  What would you like
                  <br />
                  to understand?
                </h2>
                <p>
                  Explore cybersecurity policy, frameworks, and incident
                  scenarios.
                  <br />
                  Every answer starts with your source documents.
                </p>
                <div className="suggestion-grid">
                  {suggestions.map((s) => (
                    <button
                      key={s.tag}
                      type="button"
                      onClick={() => {
                        setQuestion(s.question);
                        setValidation(null);
                        inputRef.current?.focus();
                      }}
                    >
                      <span>
                        {s.tag}
                        <ArrowUpRight size={13} />
                      </span>
                      <strong>{s.question}</strong>
                    </button>
                  ))}
                </div>
                <Link href="/knowledge-base" className="text-link subtle-link">
                  <BookOpen size={13} />
                  Explore the knowledge base
                  <ArrowRightIcon />
                </Link>
              </div>
            )}
            <div
              className="messages"
              role="log"
              aria-label="Conversation messages"
            >
              {messages.map((m) => (
                <article key={m.id} className={`message message-${m.role}`}>
                  <div className="message-avatar">
                    {m.role === "user" ? "You" : <BrandMark />}
                  </div>
                  <div className="message-body">
                    <div className="message-heading">
                      <strong>{m.role === "user" ? "You" : "CyberSage"}</strong>
                      {m.response && (
                        <span>{m.response.status.replaceAll("_", " ")}</span>
                      )}
                    </div>
                    {m.response?.context_used && (
                      <p className="resolved-question">
                        Contextual question: {m.response.resolved_message}
                      </p>
                    )}
                    {m.role === "assistant" ? (
                      <SafeMarkdown>{m.content}</SafeMarkdown>
                    ) : (
                      <p className="user-message-content">{m.content}</p>
                    )}
                    {m.response && (
                      <>
                        <CitationList citations={m.response.citations ?? []} />
                        {m.response.assessment && (
                          <Badge>
                            {m.response.assessment.category} ·{" "}
                            {m.response.assessment.score}/25 · Illustrative
                            matrix
                          </Badge>
                        )}
                        <div className="answer-actions">
                          <CopyAnswer text={m.content} />
                          {m.response.model && <span>{m.response.model}</span>}
                        </div>
                      </>
                    )}
                  </div>
                </article>
              ))}
            </div>
            {pending && (
              <div className="pending-answer" role="status">
                <LoaderCircle className="spin" size={17} />
                <div>
                  <strong>Working on your request</strong>
                  <p>CyberSage will return the complete response when ready.</p>
                </div>
              </div>
            )}
            {error && (
              <div className="chat-error" role="alert">
                <TriangleAlert size={18} />
                <div>
                  <strong>The request couldn’t complete.</strong>
                  <p>{error}</p>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => retry && void send(retry)}
                    disabled={pending}
                  >
                    <RotateCcw size={13} />
                    Retry request
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      router.push(`/assistant?new=${crypto.randomUUID()}`)
                    }
                  >
                    Start a new conversation
                  </Button>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
          <form
            className="composer"
            onSubmit={(e) => {
              e.preventDefault();
              void send();
            }}
          >
            <div className="composer-input">
              <label className="sr-only" htmlFor="assistant-message">
                Your cybersecurity question
              </label>
              <Textarea
                ref={inputRef}
                id="assistant-message"
                value={question}
                onChange={(e) => {
                  setQuestion(e.target.value);
                  setValidation(null);
                }}
                onKeyDown={(e) => {
                  if (
                    e.key === "Enter" &&
                    !e.shiftKey &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    void send();
                  }
                }}
                placeholder="Ask a cybersecurity question…"
                maxLength={2000}
                rows={2}
                disabled={
                  pending ||
                  loadingHistory ||
                  Boolean(historyError) ||
                  Boolean(retry)
                }
                aria-invalid={Boolean(validation)}
                aria-describedby={
                  validation ? "question-error" : "composer-help"
                }
              />
              <Button
                size="icon"
                type="submit"
                aria-label="Send question"
                disabled={
                  pending ||
                  loadingHistory ||
                  Boolean(historyError) ||
                  Boolean(retry)
                }
              >
                {pending ? (
                  <LoaderCircle size={17} className="spin" />
                ) : (
                  <ArrowUp size={18} />
                )}
              </Button>
            </div>
            {validation && (
              <p className="form-error" id="question-error" role="alert">
                {validation}
              </p>
            )}
            <div className="composer-meta" id="composer-help">
              <span>
                Enter to send <span>·</span> Shift + Enter for a new line
              </span>
              <span>{question.length}/2,000</span>
            </div>
            <p className="chat-disclaimer">
              <ShieldCheck size={11} />
              Answers can be incomplete. Inspect citations and source context.
              No token streaming is used.
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}
function ArrowRightIcon() {
  return <span aria-hidden="true">→</span>;
}
