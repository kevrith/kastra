import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithRouter, userOnPlan } from "../../test/utils";
import Expenses from "./Expenses";

// The page is wrapped in UpgradeGate, which reads the plan off the user.
const mockUseAuth = vi.fn();
vi.mock("../../context/AuthContext", () => ({ useAuth: () => mockUseAuth() }));

vi.mock("../../api/expenses", () => ({
  getExpenses: vi.fn(),
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
}));
vi.mock("../../api/ai", () => ({ categorizeExpense: vi.fn() }));

import { getExpenses, createExpense, updateExpense, deleteExpense } from "../../api/expenses";

const expense = (over = {}) => ({
  id: "e1",
  category: "materials",
  description: "Cement for slab",
  vendor: "Nairobi Hardware",
  amount: 12000,
  date: "2026-06-15",
  ...over,
});

function respondWith(rows, metaOver = {}) {
  getExpenses.mockResolvedValue({
    data: {
      data: rows,
      meta: { page: 1, limit: 20, total: rows.length, pages: 1, ...metaOver },
    },
  });
}

function renderPage(plan = "business") {
  mockUseAuth.mockReturnValue({ user: userOnPlan(plan) });
  return renderWithRouter(<Expenses />);
}

beforeEach(() => {
  vi.clearAllMocks();
  respondWith([]);
  createExpense.mockResolvedValue({});
  updateExpense.mockResolvedValue({});
  deleteExpense.mockResolvedValue({});
});

describe("Expenses page — plan gating", () => {
  it("shows the upgrade prompt on the free plan", async () => {
    renderPage("free");
    expect(await screen.findByText(/Track business expenses/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Expenses" })).not.toBeInTheDocument();
  });

  it("shows the real page from starter upwards", async () => {
    renderPage("starter");
    expect(await screen.findByRole("heading", { name: "Expenses" })).toBeInTheDocument();
  });
});

describe("Expenses page — listing", () => {
  it("loads the first page on mount", async () => {
    renderPage();
    await waitFor(() =>
      expect(getExpenses).toHaveBeenCalledWith({ page: 1, limit: 20, category: undefined })
    );
  });

  it("shows an empty state when there is nothing recorded", async () => {
    renderPage();
    expect(await screen.findByText(/No expenses yet/)).toBeInTheDocument();
  });

  it("renders an expense row with its details", async () => {
    respondWith([expense()]);
    renderPage();

    // Scoped to the row: "materials" is also a filter button, and the amount
    // repeats in the page-total footer.
    const row = (await screen.findByText("Cement for slab")).closest("tr");
    expect(within(row).getByText("materials")).toBeInTheDocument();
    expect(within(row).getByText("Nairobi Hardware")).toBeInTheDocument();
    expect(within(row).getByText("KSh 12,000.00")).toBeInTheDocument();
  });

  it("falls back to a dash for a missing vendor", async () => {
    respondWith([expense({ vendor: null })]);
    renderPage();
    const row = (await screen.findByText("Cement for slab")).closest("tr");
    expect(within(row).getByText("—")).toBeInTheDocument();
  });

  it("pluralises the total count", async () => {
    respondWith([expense()], { total: 1 });
    const view = renderPage();
    expect(await screen.findByText("1 total expense")).toBeInTheDocument();
    view.unmount();

    respondWith([expense(), expense({ id: "e2" })], { total: 2 });
    renderPage();
    expect(await screen.findByText("2 total expenses")).toBeInTheDocument();
  });
});

describe("Expenses page — filtering", () => {
  it("refetches scoped to the category you pick", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    await userEvent.click(screen.getByRole("button", { name: "fuel" }));
    await waitFor(() =>
      expect(getExpenses).toHaveBeenLastCalledWith({ page: 1, limit: 20, category: "fuel" })
    );
  });

  it("clears the filter with All", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    await userEvent.click(screen.getByRole("button", { name: "fuel" }));
    await userEvent.click(screen.getByRole("button", { name: "All" }));
    await waitFor(() =>
      expect(getExpenses).toHaveBeenLastCalledWith({ page: 1, limit: 20, category: undefined })
    );
  });

  it("returns to page one when the filter changes", async () => {
    respondWith([expense()], { pages: 3 });
    renderPage();
    await screen.findByText("Cement for slab");

    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(getExpenses).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 })
    ));

    await userEvent.click(screen.getByRole("button", { name: "fuel" }));
    await waitFor(() => expect(getExpenses).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 1, category: "fuel" })
    ));
  });
});

describe("Expenses page — creating", () => {
  const fillForm = async (over = {}) => {
    const form = { description: "Diesel for generator", amount: "4500", ...over };
    await userEvent.type(
      screen.getByPlaceholderText("e.g. Monthly office rent"), form.description
    );
    await userEvent.type(screen.getByRole("spinbutton"), form.amount);
    return form;
  };

  it("opens a blank Add form", async () => {
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add Expense/ }));

    expect(screen.getByRole("heading", { name: "Add Expense" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. Monthly office rent")).toHaveValue("");
  });

  it("posts the new expense and reloads the list", async () => {
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add Expense/ }));
    await fillForm();

    const dialog = screen.getByRole("heading", { name: "Add Expense" }).closest("div").parentElement;
    await userEvent.click(within(dialog).getByRole("button", { name: "Add Expense" }));

    await waitFor(() => expect(createExpense).toHaveBeenCalledWith(
      expect.objectContaining({
        description: "Diesel for generator",
        amount: 4500,
        category: "other",
      })
    ));
    await waitFor(() => expect(getExpenses).toHaveBeenCalledTimes(2));
  });

  it("sends a blank vendor as null rather than an empty string", async () => {
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add Expense/ }));
    await fillForm();

    const dialog = screen.getByRole("heading", { name: "Add Expense" }).closest("div").parentElement;
    await userEvent.click(within(dialog).getByRole("button", { name: "Add Expense" }));

    await waitFor(() => expect(createExpense).toHaveBeenCalledWith(
      expect.objectContaining({ vendor: null })
    ));
  });

  it("refuses to save without a description or amount", async () => {
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add Expense/ }));

    const dialog = screen.getByRole("heading", { name: "Add Expense" }).closest("div").parentElement;
    await userEvent.click(within(dialog).getByRole("button", { name: "Add Expense" }));

    expect(createExpense).not.toHaveBeenCalled();
  });

  it("keeps the chosen category", async () => {
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: /Add Expense/ }));
    await userEvent.selectOptions(screen.getByRole("combobox"), "fuel");
    await fillForm();

    const dialog = screen.getByRole("heading", { name: "Add Expense" }).closest("div").parentElement;
    await userEvent.click(within(dialog).getByRole("button", { name: "Add Expense" }));

    await waitFor(() => expect(createExpense).toHaveBeenCalledWith(
      expect.objectContaining({ category: "fuel" })
    ));
  });
});

describe("Expenses page — editing", () => {
  it("prefills the form from the row", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    const row = screen.getByText("Cement for slab").closest("tr");
    await userEvent.click(within(row).getAllByRole("button")[0]);

    expect(screen.getByRole("heading", { name: "Edit Expense" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. Monthly office rent")).toHaveValue("Cement for slab");
    expect(screen.getByPlaceholderText("Optional")).toHaveValue("Nairobi Hardware");
    expect(screen.getByRole("spinbutton")).toHaveValue(12000);
  });

  it("puts the edit through as an update, not a create", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    const row = screen.getByText("Cement for slab").closest("tr");
    await userEvent.click(within(row).getAllByRole("button")[0]);
    await userEvent.click(screen.getByRole("button", { name: "Save Changes" }));

    await waitFor(() => expect(updateExpense).toHaveBeenCalledWith("e1", expect.any(Object)));
    expect(createExpense).not.toHaveBeenCalled();
  });

  it("offers no receipt scan while editing", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    const row = screen.getByText("Cement for slab").closest("tr");
    await userEvent.click(within(row).getAllByRole("button")[0]);
    expect(screen.queryByRole("button", { name: /Scan Receipt/ })).not.toBeInTheDocument();
  });
});

describe("Expenses page — deleting", () => {
  it("asks before deleting", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    const row = screen.getByText("Cement for slab").closest("tr");
    await userEvent.click(within(row).getAllByRole("button")[1]);

    expect(screen.getByText(/Delete "Cement for slab"\? This cannot be undone\./)).toBeInTheDocument();
    expect(deleteExpense).not.toHaveBeenCalled();
  });

  it("deletes on confirm and reloads", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    const row = screen.getByText("Cement for slab").closest("tr");
    await userEvent.click(within(row).getAllByRole("button")[1]);
    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));

    await waitFor(() => expect(deleteExpense).toHaveBeenCalledWith("e1"));
    await waitFor(() => expect(getExpenses).toHaveBeenCalledTimes(2));
  });

  it("keeps the expense when you cancel", async () => {
    respondWith([expense()]);
    renderPage();
    await screen.findByText("Cement for slab");

    const row = screen.getByText("Cement for slab").closest("tr");
    await userEvent.click(within(row).getAllByRole("button")[1]);
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(deleteExpense).not.toHaveBeenCalled();
  });
});
