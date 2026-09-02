import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

/**
 * Render a component inside a router.
 *
 * Most components in this app call `useNavigate` or render a `<Link>`, both of
 * which throw outside a router. `route` seeds the initial history entry.
 */
export function renderWithRouter(ui, { route = "/", ...options } = {}) {
  return render(ui, {
    wrapper: ({ children }) => (
      <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
    ),
    ...options,
  });
}

/** A user object shaped like the one `/api/auth/me` returns. */
export function userOnPlan(plan, orgOverrides = {}) {
  return {
    id: "user-1",
    email: "owner@example.com",
    display_name: "Owner",
    role: "admin",
    organization: { id: "org-1", name: "Test Biz", plan, ...orgOverrides },
  };
}
