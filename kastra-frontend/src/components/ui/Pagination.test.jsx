import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Pagination from "./Pagination";

const meta = (over = {}) => ({ page: 1, limit: 20, total: 100, pages: 5, ...over });

describe("Pagination", () => {
  it("renders nothing when there is only one page", () => {
    const { container } = render(<Pagination meta={meta({ pages: 1 })} onPageChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing without meta", () => {
    const { container } = render(<Pagination meta={null} onPageChange={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("describes the visible slice of the first page", () => {
    render(<Pagination meta={meta()} onPageChange={vi.fn()} />);
    expect(screen.getByText(/Showing 1–20 of 100/)).toBeInTheDocument();
  });

  it("describes the visible slice of a middle page", () => {
    render(<Pagination meta={meta({ page: 3 })} onPageChange={vi.fn()} />);
    expect(screen.getByText(/Showing 41–60 of 100/)).toBeInTheDocument();
  });

  it("clamps the upper bound on a partial last page", () => {
    render(<Pagination meta={meta({ page: 5, total: 87 })} onPageChange={vi.fn()} />);
    expect(screen.getByText(/Showing 81–87 of 87/)).toBeInTheDocument();
  });

  it("disables previous on the first page", () => {
    render(<Pagination meta={meta({ page: 1 })} onPageChange={vi.fn()} />);
    const [prev, next] = screen.getAllByRole("button");
    expect(prev).toBeDisabled();
    expect(next).toBeEnabled();
  });

  it("disables next on the last page", () => {
    render(<Pagination meta={meta({ page: 5 })} onPageChange={vi.fn()} />);
    const [prev, next] = screen.getAllByRole("button");
    expect(prev).toBeEnabled();
    expect(next).toBeDisabled();
  });

  it("steps forward and back by one page", async () => {
    const onPageChange = vi.fn();
    render(<Pagination meta={meta({ page: 3 })} onPageChange={onPageChange} />);
    const [prev, next] = screen.getAllByRole("button");

    await userEvent.click(next);
    expect(onPageChange).toHaveBeenCalledWith(4);

    await userEvent.click(prev);
    expect(onPageChange).toHaveBeenCalledWith(2);
  });
});
