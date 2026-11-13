"use client";
import { useMemo, useSyncExternalStore } from "react";
const KEY = "cybersage.recent.v1";
export interface RecentConversation {
  id: string;
  title: string;
  updated: string;
}
const subscribe = (callback: () => void) => {
  window.addEventListener("storage", callback);
  window.addEventListener("cybersage:recent", callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener("cybersage:recent", callback);
  };
};
function snapshot() {
  try {
    return localStorage.getItem(KEY) ?? "[]";
  } catch {
    return "[]";
  }
}
function parse(raw: string): RecentConversation[] {
  try {
    const data: unknown = JSON.parse(raw);
    return Array.isArray(data)
      ? data
          .filter(
            (r): r is RecentConversation =>
              typeof r?.id === "string" &&
              typeof r?.title === "string" &&
              typeof r?.updated === "string",
          )
          .slice(0, 8)
      : [];
  } catch {
    return [];
  }
}
export function useRecentConversations() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => "[]");
  return useMemo(() => parse(raw), [raw]);
}
export function rememberConversation(id: string, title: string) {
  try {
    const current = parse(snapshot());
    const old = current.find((r) => r.id === id);
    localStorage.setItem(
      KEY,
      JSON.stringify(
        [
          {
            id,
            title: old?.title ?? title.slice(0, 54),
            updated: new Date().toISOString(),
          },
          ...current.filter((r) => r.id !== id),
        ].slice(0, 8),
      ),
    );
    window.dispatchEvent(new Event("cybersage:recent"));
  } catch {
    /* Storage disabled: current conversation still works in memory. */
  }
}
export function clearRecentConversations() {
  try {
    localStorage.removeItem(KEY);
    window.dispatchEvent(new Event("cybersage:recent"));
  } catch {
    /* Browser storage may be unavailable. */
  }
}
