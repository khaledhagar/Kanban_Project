"use client";

import { useState, type FormEvent } from "react";
import clsx from "clsx";
import { sendChat, type ChatTurn } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type ChatSidebarProps = {
  // Called with the persisted board whenever the assistant replies, so the
  // board UI refreshes automatically when the AI changes it.
  onBoardUpdate: (board: BoardData) => void;
};

export const ChatSidebar = ({ onBoardUpdate }: ChatSidebarProps) => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const text = input.trim();
    if (!text || sending) {
      return;
    }

    const history = messages;
    setMessages([...history, { role: "user", content: text }]);
    setInput("");
    setSending(true);
    try {
      const { reply, board } = await sendChat(text, history);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      onBoardUpdate(board);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong." },
      ]);
    } finally {
      setSending(false);
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-40 rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold uppercase tracking-wide text-white shadow-[var(--shadow)] transition hover:brightness-110"
      >
        Open assistant
      </button>
    );
  }

  return (
    <aside className="fixed bottom-6 right-6 z-40 flex h-[min(540px,80vh)] w-[min(380px,92vw)] flex-col overflow-hidden rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] shadow-[var(--shadow)]">
      <header className="flex items-center justify-between border-b border-[var(--stroke)] px-5 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            Assistant
          </p>
          <p className="font-display text-lg font-semibold text-[var(--navy-dark)]">
            Ask about your board
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-label="Close assistant"
          className="rounded-full border border-[var(--stroke)] px-3 py-1 text-xs font-semibold text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
        >
          Close
        </button>
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 ? (
          <p className="text-sm leading-6 text-[var(--gray-text)]">
            Try &quot;Add a card to Backlog&quot; or &quot;Move the review card to
            Done&quot;. I can create, edit, and move cards.
          </p>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={clsx(
                "max-w-[85%] rounded-2xl px-3 py-2 text-sm leading-6",
                message.role === "user"
                  ? "ml-auto bg-[var(--primary-blue)] text-white"
                  : "mr-auto border border-[var(--stroke)] bg-[var(--surface)] text-[var(--navy-dark)]"
              )}
            >
              {message.content}
            </div>
          ))
        )}
        {sending && (
          <p className="mr-auto text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
            Thinking...
          </p>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 border-t border-[var(--stroke)] px-4 py-3"
      >
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          aria-label="Message"
          placeholder="Ask the assistant..."
          className="flex-1 rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
        />
        <button
          type="submit"
          disabled={sending}
          className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-60"
        >
          Send
        </button>
      </form>
    </aside>
  );
};
