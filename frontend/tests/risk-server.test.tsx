import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { RiskWorkspace } from "@/components/risk-workspace";
import { api } from "@/lib/api";
import { assessRisk } from "@/lib/risk";
import { agentFixture } from "./fixtures";
afterEach(() => vi.restoreAllMocks());
it("shows a local preview separately from a backend-confirmed assessment", async () => {
  const invoke = vi.spyOn(api, "invoke").mockResolvedValue(
    agentFixture({
      capability: "risk",
      status: "assessed",
      answer: null,
      assessment: assessRisk(4, 5),
      model: null,
    }),
  );
  const user = userEvent.setup();
  render(<RiskWorkspace />);
  expect(
    screen.queryByText("Server confirmed · Critical"),
  ).not.toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Likelihood 4: Likely" }),
  );
  await user.click(screen.getByRole("button", { name: "Impact 5: Severe" }));
  await user.click(screen.getByRole("button", { name: "Confirm assessment" }));
  expect(
    await screen.findByText("Server confirmed · Critical"),
  ).toBeInTheDocument();
  expect(invoke.mock.calls[0][0]).toMatchObject({
    message: "Calculate risk",
    likelihood: 4,
    impact: 5,
  });
  await user.click(
    screen.getByRole("button", { name: "Impact 1: Negligible" }),
  );
  expect(screen.getByText(/Inputs changed/)).toBeInTheDocument();
});
it("retries a failed assessment with the same request ID", async () => {
  const invoke = vi
    .spyOn(api, "invoke")
    .mockRejectedValueOnce(new Error("Service unavailable"))
    .mockResolvedValue(
      agentFixture({
        capability: "risk",
        status: "assessed",
        answer: null,
        assessment: assessRisk(3, 4),
        model: null,
      }),
    );
  const user = userEvent.setup();
  render(<RiskWorkspace />);
  await user.click(screen.getByRole("button", { name: "Confirm assessment" }));
  await user.click(
    await screen.findByRole("button", { name: "Retry assessment" }),
  );
  expect(invoke.mock.calls[0][0]).toEqual(invoke.mock.calls[1][0]);
  expect(
    await screen.findByText("Server confirmed · High"),
  ).toBeInTheDocument();
});
