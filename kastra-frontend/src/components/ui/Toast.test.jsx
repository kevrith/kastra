import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Toast from "./Toast";

describe("Toast", () => {
  it("shows the message", () => {
    render(<Toast message="Invoice saved" type="success" onClose={vi.fn()} />);
    expect(screen.getByText("Invoice saved")).toBeInTheDocument();
  });

  it("closes from the X button", async () => {
    const onClose = vi.fn();
    render(<Toast message="Oops" onClose={onClose} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("styles each type distinctly", () => {
    const { rerender, container } = render(<Toast message="m" type="error" onClose={vi.fn()} />);
    expect(container.querySelector(".bg-red-50")).toBeInTheDocument();

    rerender(<Toast message="m" type="success" onClose={vi.fn()} />);
    expect(container.querySelector(".bg-green-50")).toBeInTheDocument();

    rerender(<Toast message="m" type="info" onClose={vi.fn()} />);
    expect(container.querySelector(".bg-blue-50")).toBeInTheDocument();
  });

  describe("auto-dismiss", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());

    it("closes itself after the default duration", () => {
      const onClose = vi.fn();
      render(<Toast message="m" onClose={onClose} />);

      act(() => vi.advanceTimersByTime(3999));
      expect(onClose).not.toHaveBeenCalled();

      act(() => vi.advanceTimersByTime(1));
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("honours a custom duration", () => {
      const onClose = vi.fn();
      render(<Toast message="m" duration={1000} onClose={onClose} />);

      act(() => vi.advanceTimersByTime(1000));
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("stays put when duration is 0", () => {
      const onClose = vi.fn();
      render(<Toast message="m" duration={0} onClose={onClose} />);

      act(() => vi.advanceTimersByTime(60000));
      expect(onClose).not.toHaveBeenCalled();
    });

    it("cancels its timer on unmount so it cannot fire late", () => {
      const onClose = vi.fn();
      const { unmount } = render(<Toast message="m" onClose={onClose} />);
      unmount();

      act(() => vi.advanceTimersByTime(10000));
      expect(onClose).not.toHaveBeenCalled();
    });
  });
});
