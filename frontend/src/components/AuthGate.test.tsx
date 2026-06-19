import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";
import { AuthGate } from "@/components/AuthGate";

// Route fetch by path so api.ts runs against a fake backend.
const mockFetch = (authenticated: boolean) =>
  vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/me")) {
      return {
        ok: authenticated,
        json: async () => ({ username: "user" }),
      } as unknown as Response;
    }
    return { ok: true, json: async () => ({ ok: true }) } as unknown as Response;
  });

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AuthGate", () => {
  it("shows the login form when not authenticated", async () => {
    vi.stubGlobal("fetch", mockFetch(false));
    render(<AuthGate />);
    expect(
      await screen.findByRole("heading", { name: /sign in/i })
    ).toBeInTheDocument();
  });

  it("shows the board when authenticated, then returns to login on logout", async () => {
    vi.stubGlobal("fetch", mockFetch(true));
    render(<AuthGate />);

    expect(
      await screen.findByRole("heading", { name: /kanban studio/i })
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /log out/i }));

    expect(
      await screen.findByRole("heading", { name: /sign in/i })
    ).toBeInTheDocument();
  });
});
