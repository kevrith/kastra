import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithRouter, userOnPlan } from "../../test/utils";
import TrialBanner from "./TrialBanner";

const mockUseAuth = vi.fn();
vi.mock("../../context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => mockNavigate,
}));

const NOW = new Date("2026-06-15T12:00:00Z");
const daysFromNow = (n) => new Date(NOW.getTime() + n * 86400000).toISOString();

function renderBanner(org) {
  mockUseAuth.mockReturnValue({ user: org ? userOnPlan("starter", org) : null });
  return renderWithRouter(<TrialBanner />);
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(NOW);
  sessionStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  sessionStorage.clear();
});

describe("TrialBanner", () => {
  it("stays hidden when the org is not on a trial", () => {
    const { container } = renderBanner({ is_trial: false, trial_ends_at: daysFromNow(10) });
    expect(container).toBeEmptyDOMElement();
  });

  it("stays hidden when there is no trial end date", () => {
    const { container } = renderBanner({ is_trial: true, trial_ends_at: null });
    expect(container).toBeEmptyDOMElement();
  });

  it("stays hidden for a signed-out visitor", () => {
    const { container } = renderBanner(null);
    expect(container).toBeEmptyDOMElement();
  });

  it("counts down the remaining days", () => {
    renderBanner({ is_trial: true, trial_ends_at: daysFromNow(10) });
    expect(screen.getByText(/10 days remaining/)).toBeInTheDocument();
  });

  it("uses the singular on the last full day", () => {
    renderBanner({ is_trial: true, trial_ends_at: daysFromNow(0.5) });
    expect(screen.getByText(/1 day remaining/)).toBeInTheDocument();
    expect(screen.queryByText(/1 days remaining/)).not.toBeInTheDocument();
  });

  it("says the trial ends today once the date has passed", () => {
    renderBanner({ is_trial: true, trial_ends_at: daysFromNow(-1) });
    expect(screen.getByText(/trial ends today/)).toBeInTheDocument();
  });

  it("escalates to red inside three days", () => {
    const { container } = renderBanner({ is_trial: true, trial_ends_at: daysFromNow(2) });
    expect(container.querySelector(".bg-red-600")).toBeInTheDocument();
  });

  it("warns in yellow inside a week", () => {
    const { container } = renderBanner({ is_trial: true, trial_ends_at: daysFromNow(5) });
    expect(container.querySelector(".bg-yellow-500")).toBeInTheDocument();
  });

  it("stays green when there is plenty of time left", () => {
    const { container } = renderBanner({ is_trial: true, trial_ends_at: daysFromNow(20) });
    expect(container.querySelector(".bg-green-600")).toBeInTheDocument();
  });

  it("sends the upgrade click to settings", async () => {
    renderBanner({ is_trial: true, trial_ends_at: daysFromNow(10) });
    await userEvent.click(screen.getByRole("button", { name: /Upgrade now/ }));
    expect(mockNavigate).toHaveBeenCalledWith("/settings");
  });

  it("disappears once dismissed", async () => {
    const { container } = renderBanner({ is_trial: true, trial_ends_at: daysFromNow(10) });
    const [, dismiss] = screen.getAllByRole("button");

    await userEvent.click(dismiss);
    expect(container).toBeEmptyDOMElement();
  });

  it("stays dismissed for the rest of the day", async () => {
    const org = { is_trial: true, trial_ends_at: daysFromNow(10) };
    const first = renderBanner(org);
    await userEvent.click(screen.getAllByRole("button")[1]);
    first.unmount();

    const { container } = renderBanner(org);
    expect(container).toBeEmptyDOMElement();
  });

  it("comes back the next day", async () => {
    const org = { is_trial: true, trial_ends_at: daysFromNow(10) };
    const first = renderBanner(org);
    await userEvent.click(screen.getAllByRole("button")[1]);
    first.unmount();

    vi.setSystemTime(new Date(NOW.getTime() + 86400000));
    renderBanner(org);
    expect(screen.getByText(/remaining/)).toBeInTheDocument();
  });
});
