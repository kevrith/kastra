import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProductAutocomplete from "./ProductAutocomplete";

vi.mock("../../api/products", () => ({ getProducts: vi.fn() }));
import { getProducts } from "../../api/products";

const PRODUCT = { id: "p1", name: "Cement 50kg", unit_price: 750, cost_price: 600, client_price: null };

let user;

beforeEach(() => {
  vi.clearAllMocks();
  getProducts.mockResolvedValue({ data: [PRODUCT] });
  vi.useFakeTimers({ shouldAdvanceTime: true });
  user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
});

afterEach(() => vi.useRealTimers());

const settleDebounce = async () => { await act(async () => { vi.advanceTimersByTime(250); }); };

describe("ProductAutocomplete", () => {
  it("does not query on an empty box", async () => {
    render(<ProductAutocomplete value="" onChange={vi.fn()} onSelect={vi.fn()} />);
    await settleDebounce();
    expect(getProducts).not.toHaveBeenCalled();
  });

  it("queries once the user has typed something", async () => {
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={vi.fn()} />);
    await settleDebounce();
    await waitFor(() => expect(getProducts).toHaveBeenCalledWith("cem", undefined));
  });

  it("passes the client through so agreed rates can be applied", async () => {
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={vi.fn()} clientId="c1" />);
    await settleDebounce();
    await waitFor(() => expect(getProducts).toHaveBeenCalledWith("cem", "c1"));
  });

  it("lists matches with their price", async () => {
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={vi.fn()} />);
    await settleDebounce();
    expect(await screen.findByText("Cement 50kg")).toBeInTheDocument();
    expect(screen.getByText(/KSh 750\.00/)).toBeInTheDocument();
  });

  it("stays closed when nothing matches", async () => {
    getProducts.mockResolvedValue({ data: [] });
    const { container } = render(
      <ProductAutocomplete value="zzz" onChange={vi.fn()} onSelect={vi.fn()} />
    );
    await settleDebounce();
    await waitFor(() => expect(getProducts).toHaveBeenCalled());
    expect(container.querySelector("ul")).not.toBeInTheDocument();
  });

  it("fills the row from the picked product", async () => {
    const onSelect = vi.fn();
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={onSelect} />);
    await settleDebounce();

    await user.click(await screen.findByText("Cement 50kg"));
    expect(onSelect).toHaveBeenCalledWith({
      description: "Cement 50kg", unit_price: 750, cost_price: 600,
    });
  });

  it("prefers the client's agreed rate over the list price", async () => {
    getProducts.mockResolvedValue({
      data: [{ ...PRODUCT, client_price: 690 }],
    });
    const onSelect = vi.fn();
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={onSelect} clientId="c1" />);
    await settleDebounce();

    await user.click(await screen.findByText("Cement 50kg"));
    expect(onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ unit_price: 690 })
    );
  });

  it("flags an agreed rate in the dropdown", async () => {
    getProducts.mockResolvedValue({ data: [{ ...PRODUCT, client_price: 690 }] });
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={vi.fn()} clientId="c1" />);
    await settleDebounce();

    expect(await screen.findByText("agreed rate")).toBeInTheDocument();
    expect(screen.getByText(/KSh 690\.00/)).toBeInTheDocument();
  });

  it("does not flag an agreed rate when there is none", async () => {
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={vi.fn()} />);
    await settleDebounce();
    await screen.findByText("Cement 50kg");
    expect(screen.queryByText("agreed rate")).not.toBeInTheDocument();
  });

  it("treats a zero agreed rate as a real price, not a missing one", async () => {
    getProducts.mockResolvedValue({ data: [{ ...PRODUCT, client_price: 0 }] });
    const onSelect = vi.fn();
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={onSelect} clientId="c1" />);
    await settleDebounce();

    await user.click(await screen.findByText("Cement 50kg"));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ unit_price: 0 }));
  });

  it("defaults a missing cost price to zero", async () => {
    getProducts.mockResolvedValue({ data: [{ ...PRODUCT, cost_price: null }] });
    const onSelect = vi.fn();
    render(<ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={onSelect} />);
    await settleDebounce();

    await user.click(await screen.findByText("Cement 50kg"));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ cost_price: 0 }));
  });

  it("swallows a failed lookup instead of breaking the form", async () => {
    getProducts.mockRejectedValue(new Error("network"));
    const { container } = render(
      <ProductAutocomplete value="cem" onChange={vi.fn()} onSelect={vi.fn()} />
    );
    await settleDebounce();
    await waitFor(() => expect(getProducts).toHaveBeenCalled());
    expect(container.querySelector("input")).toBeInTheDocument();
  });

  it("reports typing back to the parent", async () => {
    const onChange = vi.fn();
    render(<ProductAutocomplete value="" onChange={onChange} onSelect={vi.fn()} />);
    await user.type(screen.getByRole("textbox"), "c");
    expect(onChange).toHaveBeenCalledWith("c");
  });
});
