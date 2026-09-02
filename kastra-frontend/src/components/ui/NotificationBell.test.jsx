import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithRouter } from "../../test/utils";
import NotificationBell from "./NotificationBell";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => mockNavigate,
}));

vi.mock("../../api/notifications", () => ({
  getNotifications: vi.fn(),
  markRead: vi.fn(),
  markAllRead: vi.fn(),
}));
import { getNotifications, markRead, markAllRead } from "../../api/notifications";

const note = (over = {}) => ({
  id: "n1",
  type: "payment_received",
  title: "Payment received",
  body: "Invoice INV-0001 has been fully paid.",
  entity_id: "INV-0001",
  read_at: null,
  created_at: new Date().toISOString(),
  ...over,
});

function respondWith(items, unread = items.filter((n) => !n.read_at).length) {
  getNotifications.mockResolvedValue({ data: { items, unread_count: unread } });
}

beforeEach(() => {
  vi.clearAllMocks();
  markRead.mockResolvedValue({});
  markAllRead.mockResolvedValue({});
});

async function openPanel() {
  await userEvent.click(await screen.findByRole("button", { name: "Notifications" }));
}

describe("NotificationBell", () => {
  it("loads notifications on mount", async () => {
    respondWith([]);
    renderWithRouter(<NotificationBell />);
    await waitFor(() => expect(getNotifications).toHaveBeenCalled());
  });

  it("shows no badge when everything is read", async () => {
    respondWith([note({ read_at: new Date().toISOString() })]);
    renderWithRouter(<NotificationBell />);
    await waitFor(() => expect(getNotifications).toHaveBeenCalled());
    expect(screen.queryByText("1")).not.toBeInTheDocument();
  });

  it("badges the unread count", async () => {
    respondWith([note({ id: "a" }), note({ id: "b" })]);
    renderWithRouter(<NotificationBell />);
    expect(await screen.findByText("2")).toBeInTheDocument();
  });

  it("caps the badge at 9+", async () => {
    respondWith(Array.from({ length: 12 }, (_, i) => note({ id: `n${i}` })));
    renderWithRouter(<NotificationBell />);
    expect(await screen.findByText("9+")).toBeInTheDocument();
  });

  it("survives a failing request without crashing", async () => {
    getNotifications.mockRejectedValue(new Error("network"));
    renderWithRouter(<NotificationBell />);
    expect(await screen.findByRole("button", { name: "Notifications" })).toBeInTheDocument();
  });

  it("shows an empty state when there is nothing to read", async () => {
    respondWith([]);
    renderWithRouter(<NotificationBell />);
    await openPanel();
    expect(screen.getByText("All caught up")).toBeInTheDocument();
  });

  it("lists notifications when opened", async () => {
    respondWith([note()]);
    renderWithRouter(<NotificationBell />);
    await openPanel();
    expect(screen.getByText("Payment received")).toBeInTheDocument();
    expect(screen.getByText(/Invoice INV-0001 has been fully paid/)).toBeInTheDocument();
  });

  it("marks a notification read and navigates to its entity", async () => {
    respondWith([note()]);
    renderWithRouter(<NotificationBell />);
    await openPanel();

    await userEvent.click(screen.getByText("Payment received"));
    expect(markRead).toHaveBeenCalledWith("n1");
    expect(mockNavigate).toHaveBeenCalledWith("/invoices/INV-0001");
  });

  it("does not re-mark an already-read notification", async () => {
    respondWith([note({ read_at: new Date().toISOString() })]);
    renderWithRouter(<NotificationBell />);
    await openPanel();

    await userEvent.click(screen.getByText("Payment received"));
    expect(markRead).not.toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith("/invoices/INV-0001");
  });

  it("routes each notification type to its own section", async () => {
    const cases = [
      ["quotation_accepted", "QT-1", "/quotations/QT-1"],
      ["rfq_supplier_response", "req-1", "/suppliers/requests/req-1"],
      ["po_supplier_response", "po-1", "/purchase-orders/po-1"],
    ];
    for (const [type, entity_id, expected] of cases) {
      vi.clearAllMocks();
      respondWith([note({ type, entity_id, title: `T-${type}` })]);
      const view = renderWithRouter(<NotificationBell />);
      await openPanel();
      await userEvent.click(screen.getByText(`T-${type}`));
      expect(mockNavigate).toHaveBeenCalledWith(expected);
      view.unmount();
    }
  });

  it("navigates nowhere for an unmapped type rather than guessing a route", async () => {
    respondWith([note({ type: "something_new", title: "Mystery" })]);
    renderWithRouter(<NotificationBell />);
    await openPanel();

    await userEvent.click(screen.getByText("Mystery"));
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("marks everything read from the panel header", async () => {
    respondWith([note({ id: "a" }), note({ id: "b" })]);
    renderWithRouter(<NotificationBell />);
    await openPanel();

    await userEvent.click(screen.getByRole("button", { name: /Mark all read/ }));
    expect(markAllRead).toHaveBeenCalledOnce();
  });

  it("offers no mark-all button when nothing is unread", async () => {
    respondWith([note({ read_at: new Date().toISOString() })]);
    renderWithRouter(<NotificationBell />);
    await openPanel();
    expect(screen.queryByRole("button", { name: /Mark all read/ })).not.toBeInTheDocument();
  });

  it("closes on a click outside the panel", async () => {
    respondWith([note()]);
    renderWithRouter(<NotificationBell />);
    await openPanel();
    expect(screen.getByText("Payment received")).toBeInTheDocument();

    await userEvent.click(document.body);
    expect(screen.queryByText("Payment received")).not.toBeInTheDocument();
  });

  it("renders relative timestamps", async () => {
    respondWith([note({ created_at: new Date(Date.now() - 2 * 3600 * 1000).toISOString() })]);
    renderWithRouter(<NotificationBell />);
    await openPanel();
    expect(screen.getByText("2h ago")).toBeInTheDocument();
  });
});
