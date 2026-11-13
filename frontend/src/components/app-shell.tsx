"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  LayoutDashboard,
  MessagesSquare,
  ChartNoAxesCombined,
  LibraryBig,
  Fingerprint,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Menu,
  ArrowUpRight,
  MessageSquare,
  Trash2,
  ShieldCheck,
} from "lucide-react";
import { MotionConfig } from "motion/react";
import { Brand } from "./brand";
import { Button } from "./ui/button";
import { Sheet } from "./ui/sheet";
import { ConnectionStatus } from "./connection-status";
import {
  clearRecentConversations,
  useRecentConversations,
} from "@/lib/conversations";

export const navigation = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/assistant", label: "AI Assistant", icon: MessagesSquare },
  { href: "/risk-analyzer", label: "Risk Analyzer", icon: ChartNoAxesCombined },
  { href: "/knowledge-base", label: "Knowledge Base", icon: LibraryBig },
  { href: "/about", label: "About CyberSage", icon: Fingerprint },
];
export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobile, setMobile] = useState(false);
  const recent = useRecentConversations();
  const title =
    navigation.find((item) => item.href === pathname)?.label ?? "Workspace";
  function sidebar(isCollapsed = false) {
    return (
      <>
        <Link
          href="/"
          aria-label={isCollapsed ? "CyberSage overview" : undefined}
          className="brand-link"
          onClick={() => setMobile(false)}
        >
          <Brand compact={isCollapsed} />
        </Link>
        <div className="sidebar-main">
          <Button
            variant="outline"
            className="new-chat"
            onClick={() => {
              setMobile(false);
              router.push(`/assistant?new=${crypto.randomUUID()}`);
            }}
            title="New conversation"
          >
            <Plus size={17} />
            {!isCollapsed && "New conversation"}
          </Button>
          {!isCollapsed && <p className="nav-label">WORKSPACE</p>}
          <nav aria-label="Primary navigation" className="primary-nav">
            {navigation.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                onClick={() => setMobile(false)}
                aria-current={pathname === href ? "page" : undefined}
                title={isCollapsed ? label : undefined}
                className={pathname === href ? "nav-link active" : "nav-link"}
              >
                <Icon size={18} />
                {!isCollapsed && <span>{label}</span>}
                {!isCollapsed && pathname === href && (
                  <span className="nav-indicator" />
                )}
              </Link>
            ))}
          </nav>
          {!isCollapsed && (
            <section
              className="recent-section"
              aria-label="Recent conversations"
            >
              <div className="recent-heading">
                <p className="nav-label">RECENT CONVERSATIONS</p>
                {recent.length > 0 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Clear local conversation shortcuts"
                    title="Clears this browser’s shortcuts, not server history"
                    onClick={clearRecentConversations}
                  >
                    <Trash2 size={13} />
                  </Button>
                )}
              </div>
              {recent.length ? (
                recent.map((r) => (
                  <Link
                    className="recent-link"
                    key={r.id}
                    href={`/assistant?conversation=${encodeURIComponent(r.id)}`}
                    onClick={() => setMobile(false)}
                  >
                    <MessageSquare size={14} />
                    <span>{r.title}</span>
                  </Link>
                ))
              ) : (
                <p className="recent-empty">
                  Your conversations will appear here.
                  <br />
                  Start with a question.
                </p>
              )}
            </section>
          )}
        </div>
        <div className="sidebar-bottom">
          {!isCollapsed && (
            <div className="grounding-note">
              <ShieldCheck size={18} />
              <div>
                <strong>Evidence comes first.</strong>
                <p>Grounded in your knowledge base.</p>
              </div>
            </div>
          )}
          <Link
            href="/about"
            className="workspace-label"
            onClick={() => setMobile(false)}
          >
            <span className="workspace-avatar">CS</span>
            {!isCollapsed && (
              <>
                <span>
                  Research workspace<small>CyberSage · Local development</small>
                </span>
                <ArrowUpRight size={14} />
              </>
            )}
          </Link>
        </div>
      </>
    );
  }
  return (
    <MotionConfig reducedMotion="user">
      <a href="#main-content" className="skip-link">
        Skip to content
      </a>
      <div className={`app-shell ${collapsed ? "is-collapsed" : ""}`}>
        <aside className="desktop-sidebar">
          {sidebar(collapsed)}
          <Button
            className="collapse-control"
            variant="ghost"
            size="icon"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? (
              <PanelLeftOpen size={16} />
            ) : (
              <PanelLeftClose size={16} />
            )}
          </Button>
        </aside>
        <div className="workspace">
          <header className="topbar">
            <div className="topbar-left">
              <div className="mobile-nav">
                <Sheet
                  open={mobile}
                  onOpenChange={setMobile}
                  trigger={
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Open navigation"
                    >
                      <Menu size={21} />
                    </Button>
                  }
                >
                  {sidebar(false)}
                </Sheet>
              </div>
              <span className="breadcrumb-root">Workspace</span>
              <span className="breadcrumb-divider">/</span>
              <span>{title}</span>
            </div>
            <div className="topbar-right">
              <span className="local-label">LOCAL WORKSPACE</span>
              <ConnectionStatus />
            </div>
          </header>
          <main id="main-content" className="main-content" tabIndex={-1}>
            {children}
          </main>
          <footer className="workspace-footer">
            <span>
              CyberSage <span className="footer-divider">/</span> Cybersecurity
              intelligence, with context.
            </span>
            <span>Evidence over assumptions.</span>
          </footer>
        </div>
      </div>
    </MotionConfig>
  );
}
