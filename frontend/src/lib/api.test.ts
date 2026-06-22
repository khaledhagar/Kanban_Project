import { afterEach, expect, vi } from "vitest";
import { getBoard, saveBoard } from "@/lib/api";
import { initialData } from "@/lib/kanban";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("board API client", () => {
  it("getBoard maps the JSON response to BoardData", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => initialData,
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);

    const board = await getBoard();
    expect(board).toEqual(initialData);
    expect(fetchMock).toHaveBeenCalledWith("/api/board", {
      credentials: "include",
    });
  });

  it("getBoard throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false })) as unknown as typeof fetch
    );
    await expect(getBoard()).rejects.toThrow(/load board/i);
  });

  it("saveBoard PUTs the board as JSON", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true }));
    vi.stubGlobal("fetch", fetchMock as unknown as typeof fetch);

    await saveBoard(initialData);

    expect(fetchMock).toHaveBeenCalledWith("/api/board", {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(initialData),
    });
  });

  it("saveBoard throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false })) as unknown as typeof fetch
    );
    await expect(saveBoard(initialData)).rejects.toThrow(/save board/i);
  });
});
