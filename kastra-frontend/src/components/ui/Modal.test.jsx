import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Modal from "./Modal";
import ConfirmDialog from "./ConfirmDialog";

describe("Modal", () => {
  it("renders nothing while closed", () => {
    const { container } = render(
      <Modal open={false} onClose={vi.fn()} title="Hidden"><p>Body</p></Modal>
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the title and children when open", () => {
    render(<Modal open onClose={vi.fn()} title="Edit client"><p>Body content</p></Modal>);
    expect(screen.getByRole("heading", { name: "Edit client" })).toBeInTheDocument();
    expect(screen.getByText("Body content")).toBeInTheDocument();
  });

  it("closes from the X button", async () => {
    const onClose = vi.fn();
    render(<Modal open onClose={onClose} title="T"><p>B</p></Modal>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes when the backdrop is clicked", async () => {
    const onClose = vi.fn();
    const { container } = render(<Modal open onClose={onClose} title="T"><p>B</p></Modal>);
    await userEvent.click(container.querySelector(".bg-black\\/40"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("does not close when the panel itself is clicked", async () => {
    const onClose = vi.fn();
    render(<Modal open onClose={onClose} title="T"><p>Body content</p></Modal>);
    await userEvent.click(screen.getByText("Body content"));
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe("ConfirmDialog", () => {
  it("shows the message with Cancel and Confirm", () => {
    render(
      <ConfirmDialog open onClose={vi.fn()} onConfirm={vi.fn()}
        title="Delete invoice" message="This cannot be undone." />
    );
    expect(screen.getByText("This cannot be undone.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirm" })).toBeInTheDocument();
  });

  it("confirming fires onConfirm and then closes", async () => {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    render(<ConfirmDialog open onClose={onClose} onConfirm={onConfirm} title="T" message="M" />);

    await userEvent.click(screen.getByRole("button", { name: "Confirm" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("cancelling closes without confirming", async () => {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    render(<ConfirmDialog open onClose={onClose} onConfirm={onConfirm} title="T" message="M" />);

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalledOnce();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("uses the danger styling only when asked", () => {
    const { rerender } = render(
      <ConfirmDialog open onClose={vi.fn()} onConfirm={vi.fn()} title="T" message="M" />
    );
    expect(screen.getByRole("button", { name: "Confirm" })).toHaveClass("btn-primary");

    rerender(
      <ConfirmDialog open onClose={vi.fn()} onConfirm={vi.fn()} title="T" message="M" danger />
    );
    expect(screen.getByRole("button", { name: "Confirm" })).toHaveClass("btn-danger");
  });
});
