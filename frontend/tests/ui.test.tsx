import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { RiskWorkspace } from "@/components/risk-workspace";
import { KnowledgeWorkspace } from "@/components/knowledge-workspace";
import { SafeMarkdown } from "@/components/safe-markdown";
import { AppShell } from "@/components/app-shell";
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/components/connection-status", () => ({
  ConnectionStatus: () => <span>API not checked in unit test</span>,
}));
it("changes risk via selectors and matrix cells, and resets inputs", async () => {
  const user = userEvent.setup();
  render(<RiskWorkspace />);
  await user.click(
    screen.getByRole("button", { name: "Likelihood 4: Likely" }),
  );
  await user.click(screen.getByRole("button", { name: "Impact 5: Severe" }));
  expect(screen.getByText("Critical risk")).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Likelihood 1, impact 2: 2, Low" }),
  );
  expect(screen.getByText("Low risk")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reset inputs" }));
  expect(screen.getByText("High risk")).toBeInTheDocument();
});
it("filters actual documents with a useful empty state and reset", async () => {
  const user = userEvent.setup();
  render(<KnowledgeWorkspace />);
  await user.type(
    screen.getByRole("textbox", { name: "Filter source documents" }),
    "nonexistent topic",
  );
  expect(screen.getByText("No matching sources.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Source type" }),
    "Synthetic examples",
  );
  expect(screen.getByText("1 of 3 sources")).toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Security Incident Casebook" }),
  ).toBeInTheDocument();
});
it("never renders raw HTML, actionable generated links or remote images", () => {
  const { container } = render(
    <SafeMarkdown>
      {
        "<script>alert(1)</script>\n\n[bad](javascript:alert(1)) ![track](https://tracker.invalid/x)\n\n**Supported text**"
      }
    </SafeMarkdown>,
  );
  expect(container.querySelector("script")).toBeNull();
  expect(container.querySelector("a")).toBeNull();
  expect(container.querySelector("img")).toBeNull();
  expect(screen.getByText("Supported text")).toBeInTheDocument();
});
it("provides all required routes, active navigation and collapsible sidebar", async () => {
  const user = userEvent.setup();
  render(
    <AppShell>
      <p>Workspace content</p>
    </AppShell>,
  );
  for (const name of [
    "Overview",
    "AI Assistant",
    "Risk Analyzer",
    "Knowledge Base",
    "About CyberSage",
  ])
    expect(screen.getByRole("link", { name })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
  expect(
    screen.getByRole("button", { name: "Expand sidebar" }),
  ).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByRole("link", { name: "Skip to content" })).toHaveAttribute(
    "href",
    "#main-content",
  );
});
