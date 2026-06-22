import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, vi } from "vitest";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

// Set by a test to make POST /api/ai/chat return a canned structured response.
let chatReply: { reply: string; board: BoardData } | null = null;

// Stub the board API: GET returns the seeded board, PUT records the payload,
// POST /api/ai/chat returns the configured chat reply.
const stubFetch = () => {
  const puts: BoardData[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    if (String(input).endsWith("/api/ai/chat")) {
      return { ok: true, json: async () => chatReply } as unknown as Response;
    }
    if (init?.method === "PUT") {
      puts.push(JSON.parse(String(init.body)) as BoardData);
      return { ok: true, json: async () => ({ ok: true }) } as unknown as Response;
    }
    return { ok: true, json: async () => initialData } as unknown as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return puts;
};

// Render and wait for the board to load from the API.
const renderBoard = async () => {
  render(<KanbanBoard />);
  await screen.findAllByTestId(/column-/i);
};

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

let puts: BoardData[];

beforeEach(() => {
  chatReply = null;
  puts = stubFetch();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("KanbanBoard", () => {
  it("loads the board from the API and renders five columns", async () => {
    await renderBoard();
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    expect(puts).toHaveLength(0); // loading alone must not persist
  });

  it("renames a column", async () => {
    await renderBoard();
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("edits an existing card", async () => {
    await renderBoard();
    const column = getFirstColumn();

    await userEvent.click(
      within(column).getByRole("button", { name: /edit align roadmap themes/i })
    );

    const titleInput = within(column).getByLabelText("Card title");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated title");

    const detailsInput = within(column).getByLabelText("Card details");
    await userEvent.clear(detailsInput);
    await userEvent.type(detailsInput, "Updated details");

    await userEvent.click(within(column).getByRole("button", { name: /save/i }));

    expect(within(column).getByText("Updated title")).toBeInTheDocument();
    expect(within(column).getByText("Updated details")).toBeInTheDocument();
    expect(
      within(column).queryByText("Align roadmap themes")
    ).not.toBeInTheDocument();
  });

  it("adds and removes a card", async () => {
    await renderBoard();
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("persists each mutation to the backend via PUT", async () => {
    await renderBoard();
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "Renamed");

    // The latest PUT carries the full board with the renamed column.
    await waitFor(() => expect(puts.length).toBeGreaterThan(0));
    const latest = puts[puts.length - 1];
    expect(latest.columns[0].title).toBe("Renamed");
    expect(latest.cards).toBeTruthy();
  });

  it("shows a loading placeholder until the board arrives", async () => {
    // A GET that never resolves keeps the board in its loading state.
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise(() => {})) as unknown as typeof fetch
    );
    render(<KanbanBoard />);
    expect(await screen.findByText(/loading board/i)).toBeInTheDocument();
    expect(screen.queryByTestId(/column-/i)).not.toBeInTheDocument();
  });

  it("rejects an edit that blanks the card title", async () => {
    await renderBoard();
    const column = getFirstColumn();
    await userEvent.click(
      within(column).getByRole("button", { name: /edit align roadmap themes/i })
    );

    const titleInput = within(column).getByLabelText("Card title");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "   "); // whitespace only
    await userEvent.click(within(column).getByRole("button", { name: /save/i }));

    // Save is rejected: still editing, and the original title is unchanged.
    expect(within(column).getByLabelText("Card title")).toBeInTheDocument();
    await userEvent.click(within(column).getByRole("button", { name: /cancel/i }));
    expect(within(column).getByText("Align roadmap themes")).toBeInTheDocument();
  });

  it("shows an empty-state when a column has no cards", async () => {
    await renderBoard();
    const column = getFirstColumn(); // Backlog: card-1, card-2
    expect(within(column).queryByText(/drop a card here/i)).not.toBeInTheDocument();

    for (const name of [/delete align roadmap themes/i, /delete gather customer signals/i]) {
      await userEvent.click(within(column).getByRole("button", { name }));
    }

    expect(within(column).getByText(/drop a card here/i)).toBeInTheDocument();
  });

  it("applies an AI board update without issuing a redundant save", async () => {
    await renderBoard();
    const baselinePuts = puts.length;

    const updated = structuredClone(initialData);
    updated.cards["card-ai"] = {
      id: "card-ai",
      title: "AI made this",
      details: "From the assistant.",
    };
    updated.columns[0].cardIds = [...updated.columns[0].cardIds, "card-ai"];
    chatReply = { reply: "Sure, added it.", board: updated };

    await userEvent.click(screen.getByRole("button", { name: /open assistant/i }));
    await userEvent.type(screen.getByLabelText(/message/i), "add a card");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    // Reply renders and the board refreshes from the server's board...
    expect(await screen.findByText("Sure, added it.")).toBeInTheDocument();
    expect(await screen.findByText("AI made this")).toBeInTheDocument();
    // ...without a redundant PUT, since the backend already persisted it.
    expect(puts.length).toBe(baselinePuts);
  });
});
