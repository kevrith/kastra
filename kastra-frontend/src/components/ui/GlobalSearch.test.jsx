import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithRouter } from "../../test/utils";
import GlobalSearch from "./GlobalSearch";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => mockNavigate,
}));

vi.mock("../../api/search", () => ({ globalSearch: vi.fn() }));
import { globalSearch } from "../../api/search";

const RESULTS = [
  { type: "client", id: "c1", label: "Acme Corp", sub: "acme@example.com" },
  { type: "invoice", id: "INV-0001", label: "INV-0001", sub: "KSh 50,000.00 · unpaid" },
];

let user;

beforeEach(() => {
  vi.clearAllMocks();
  globalSearch.mockResolvedValue({ data: RESULTS });
  vi.useFakeTimers({ shouldAdvanceTime: true });
  user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
});

afterEach(() => vi.useRealTimers());

const input = () => screen.getByPlaceholderText(/Search clients, invoices/);
const settleDebounce = async () => { await act(async () => { vi.advanceTimersByTime(300); }); };

describe("GlobalSearch", () => {
  it("does not search on a single character", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "a");
    await settleDebounce();
    expect(globalSearch).not.toHaveBeenCalled();
  });

  it("does not search on whitespace alone", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "   ");
    await settleDebounce();
    expect(globalSearch).not.toHaveBeenCalled();
  });

  it("searches once the query is long enough", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "ac");
    await settleDebounce();
    await waitFor(() => expect(globalSearch).toHaveBeenCalledWith("ac"));
  });

  it("debounces rather than firing per keystroke", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "acme");
    await settleDebounce();
    await waitFor(() => expect(globalSearch).toHaveBeenCalledTimes(1));
    expect(globalSearch).toHaveBeenCalledWith("acme");
  });

  it("trims the query it sends", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "  acme  ");
    await settleDebounce();
    await waitFor(() => expect(globalSearch).toHaveBeenCalledWith("acme"));
  });

  it("lists the results with their subtitles", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "acme");
    await settleDebounce();

    expect(await screen.findByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("acme@example.com")).toBeInTheDocument();
    expect(screen.getByText("KSh 50,000.00 · unpaid")).toBeInTheDocument();
  });

  it("navigates to the record you pick", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "acme");
    await settleDebounce();

    await user.click(await screen.findByText("Acme Corp"));
    expect(mockNavigate).toHaveBeenCalledWith("/clients/c1");
  });

  it("routes invoices to the invoice page", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "inv");
    await settleDebounce();

    await user.click(await screen.findByText("INV-0001"));
    expect(mockNavigate).toHaveBeenCalledWith("/invoices/INV-0001");
  });

  it("clears the box after picking a result", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "acme");
    await settleDebounce();

    await user.click(await screen.findByText("Acme Corp"));
    expect(input()).toHaveValue("");
  });

  it("says so when nothing matches", async () => {
    globalSearch.mockResolvedValue({ data: [] });
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "zzzz");
    await settleDebounce();

    expect(await screen.findByText(/No results for "zzzz"/)).toBeInTheDocument();
  });

  it("swallows a failed search instead of breaking the header", async () => {
    globalSearch.mockRejectedValue(new Error("network"));
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "acme");
    await settleDebounce();

    await waitFor(() => expect(globalSearch).toHaveBeenCalled());
    expect(input()).toBeInTheDocument();
  });

  it("closes the dropdown on an outside click", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "acme");
    await settleDebounce();
    expect(await screen.findByText("Acme Corp")).toBeInTheDocument();

    await user.click(document.body);
    expect(screen.queryByText("Acme Corp")).not.toBeInTheDocument();
  });

  it("drops stale results when the query falls back under two characters", async () => {
    renderWithRouter(<GlobalSearch />);
    await user.type(input(), "acme");
    await settleDebounce();
    expect(await screen.findByText("Acme Corp")).toBeInTheDocument();

    await user.clear(input());
    await user.type(input(), "a");
    await settleDebounce();
    expect(screen.queryByText("Acme Corp")).not.toBeInTheDocument();
  });
});
