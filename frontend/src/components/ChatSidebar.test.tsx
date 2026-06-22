import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, vi } from "vitest";
import { ChatSidebar } from "@/components/ChatSidebar";
import { initialData } from "@/lib/kanban";

const stubChat = (response: unknown) => {
  const fetchMock = vi.fn(async () => ({
    ok: true,
    json: async () => response,
  })) as unknown as typeof fetch;
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock as unknown as ReturnType<typeof vi.fn>;
};

const open = async () =>
  userEvent.click(screen.getByRole("button", { name: /open assistant/i }));

const send = async (text: string) => {
  await userEvent.type(screen.getByLabelText(/message/i), text);
  await userEvent.click(screen.getByRole("button", { name: /send/i }));
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ChatSidebar", () => {
  it("sends the message and renders the reply, and refreshes the board", async () => {
    const fetchMock = stubChat({ reply: "Added it", board: initialData });
    const onBoardUpdate = vi.fn();
    render(<ChatSidebar onBoardUpdate={onBoardUpdate} />);

    await open();
    await send("add a card");

    expect(await screen.findByText("Added it")).toBeInTheDocument();
    expect(screen.getByText("add a card")).toBeInTheDocument();
    expect(onBoardUpdate).toHaveBeenCalledWith(initialData);

    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body).toEqual({ message: "add a card", history: [] });
  });

  it("includes prior turns as history on the next message", async () => {
    const fetchMock = stubChat({ reply: "ok", board: initialData });
    render(<ChatSidebar onBoardUpdate={() => {}} />);

    await open();
    await send("first");
    expect(await screen.findByText("ok")).toBeInTheDocument();
    await send("second");

    const secondBody = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(secondBody).toEqual({
      message: "second",
      history: [
        { role: "user", content: "first" },
        { role: "assistant", content: "ok" },
      ],
    });
  });

  it("shows an error message when the chat call fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false })) as unknown as typeof fetch
    );
    const onBoardUpdate = vi.fn();
    render(<ChatSidebar onBoardUpdate={onBoardUpdate} />);

    await open();
    await send("do something");

    expect(
      await screen.findByText(/something went wrong/i)
    ).toBeInTheDocument();
    expect(onBoardUpdate).not.toHaveBeenCalled();
  });

  it("can be opened and closed", async () => {
    render(<ChatSidebar onBoardUpdate={() => {}} />);
    await open();
    expect(screen.getByLabelText(/message/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /close assistant/i }));
    expect(screen.queryByLabelText(/message/i)).not.toBeInTheDocument();
  });
});
