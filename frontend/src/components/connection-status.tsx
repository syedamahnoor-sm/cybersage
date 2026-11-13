"use client";
import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
export function ConnectionStatus() {
  const [status, setStatus] = useState<
    "checking" | "reachable" | "unavailable"
  >("checking");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void api
      .health(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted)
          setStatus(value.status === "healthy" ? "reachable" : "unavailable");
      })
      .catch(() => {
        if (!controller.signal.aborted) setStatus("unavailable");
      });
    return () => controller.abort();
  }, [attempt]);
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => {
        setStatus("checking");
        setAttempt((value) => value + 1);
      }}
      disabled={status === "checking"}
      title="Checks FastAPI reachability only, not PostgreSQL or Groq readiness"
      className="connection-button"
    >
      <span className={`status-dot ${status}`} />
      <span aria-live="polite">
        {status === "checking"
          ? "Checking API"
          : status === "reachable"
            ? "API reachable"
            : "API unavailable"}
      </span>
      <RefreshCw size={12} className={status === "checking" ? "spin" : ""} />
    </Button>
  );
}
