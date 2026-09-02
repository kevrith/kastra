import { describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithRouter, userOnPlan } from "../../test/utils";
import UpgradeGate from "./UpgradeGate";

// UpgradeGate reads the plan off the authenticated user; stub the context so
// each test can pick a plan without standing up the real provider.
const mockUseAuth = vi.fn();
vi.mock("../../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

function renderGate(plan, props = {}) {
  mockUseAuth.mockReturnValue({ user: plan ? userOnPlan(plan) : null });
  return renderWithRouter(
    <UpgradeGate
      feature="recurring"
      title="Recurring Invoices"
      description="Bill your retainer clients automatically."
      {...props}
    >
      <p>Real page content</p>
    </UpgradeGate>
  );
}

describe("UpgradeGate", () => {
  it("renders the real content when the plan includes the feature", () => {
    renderGate("business");
    expect(screen.getByText("Real page content")).toBeInTheDocument();
    expect(screen.queryByText(/Upgrade to/)).not.toBeInTheDocument();
  });

  it("hides the content behind an upgrade prompt on a lesser plan", () => {
    renderGate("starter");
    expect(screen.queryByText("Real page content")).not.toBeInTheDocument();
    expect(screen.getByText("Bill your retainer clients automatically.")).toBeInTheDocument();
  });

  it("names the plan that unlocks the feature", () => {
    renderGate("free");
    expect(screen.getByText(/Business plan & above/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Upgrade to Business/ })).toBeInTheDocument();
  });

  it("points the upgrade link at settings", () => {
    renderGate("free");
    expect(screen.getByRole("link", { name: /Upgrade to Business/ })).toHaveAttribute(
      "href", "/settings"
    );
  });

  it("shows the viewer's current plan", () => {
    renderGate("starter");
    expect(screen.getByText("starter")).toBeInTheDocument();
  });

  it("treats a signed-out viewer as being on free", () => {
    renderGate(null);
    expect(screen.queryByText("Real page content")).not.toBeInTheDocument();
    expect(screen.getByText("free")).toBeInTheDocument();
  });

  it("renders the selling-point bullets when given", () => {
    renderGate("free", { bullets: ["Set it once", "Never chase a retainer again"] });
    expect(screen.getByText("Set it once")).toBeInTheDocument();
    expect(screen.getByText("Never chase a retainer again")).toBeInTheDocument();
  });

  it("omits the bullet list when none are given", () => {
    const { container } = renderGate("free");
    expect(container.querySelector("ul")).not.toBeInTheDocument();
  });

  it("gates a starter feature at starter, not business", () => {
    mockUseAuth.mockReturnValue({ user: userOnPlan("starter") });
    renderWithRouter(
      <UpgradeGate feature="reports" title="Reports" description="d">
        <p>Reports content</p>
      </UpgradeGate>
    );
    expect(screen.getByText("Reports content")).toBeInTheDocument();
  });

  it("falls back to starter for a feature with no declared unlock plan", () => {
    mockUseAuth.mockReturnValue({ user: userOnPlan("free") });
    renderWithRouter(
      <UpgradeGate feature="not_a_real_feature" title="Mystery" description="d">
        <p>Hidden</p>
      </UpgradeGate>
    );
    expect(screen.getByRole("link", { name: /Upgrade to Starter/ })).toBeInTheDocument();
  });
});
