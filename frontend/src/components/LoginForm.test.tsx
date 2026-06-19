import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, vi } from "vitest";
import { LoginForm } from "@/components/LoginForm";

const response = (ok: boolean, body: unknown = {}) =>
  ({ ok, json: async () => body }) as unknown as Response;

afterEach(() => {
  vi.restoreAllMocks();
});

describe("LoginForm", () => {
  it("validates that both fields are filled before calling the API", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const onAuthed = vi.fn();

    render(<LoginForm onAuthed={onAuthed} />);
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      /enter a username and password/i
    );
    expect(fetchMock).not.toHaveBeenCalled();
    expect(onAuthed).not.toHaveBeenCalled();
  });

  it("shows an error when credentials are rejected", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => response(false)));
    const onAuthed = vi.fn();

    render(<LoginForm onAuthed={onAuthed} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /invalid username or password/i
    );
    expect(onAuthed).not.toHaveBeenCalled();
  });

  it("calls onAuthed after a successful login", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => response(true, { username: "user" })));
    const onAuthed = vi.fn();

    render(<LoginForm onAuthed={onAuthed} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(onAuthed).toHaveBeenCalledTimes(1));
  });
});
