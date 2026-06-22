import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, vi } from "vitest";
import { NewCardForm } from "@/components/NewCardForm";

const openForm = async () =>
  userEvent.click(screen.getByRole("button", { name: /add a card/i }));

describe("NewCardForm", () => {
  it("does not add a card when the title is only whitespace", async () => {
    const onAdd = vi.fn();
    render(<NewCardForm onAdd={onAdd} />);

    await openForm();
    await userEvent.type(screen.getByPlaceholderText(/card title/i), "   ");
    await userEvent.click(screen.getByRole("button", { name: /add card/i }));

    expect(onAdd).not.toHaveBeenCalled();
  });

  it("trims the title and details before adding", async () => {
    const onAdd = vi.fn();
    render(<NewCardForm onAdd={onAdd} />);

    await openForm();
    await userEvent.type(screen.getByPlaceholderText(/card title/i), "  Plan  ");
    await userEvent.type(screen.getByPlaceholderText(/details/i), "  notes  ");
    await userEvent.click(screen.getByRole("button", { name: /add card/i }));

    expect(onAdd).toHaveBeenCalledWith("Plan", "notes");
    // Form closes after adding.
    expect(screen.getByRole("button", { name: /add a card/i })).toBeInTheDocument();
  });

  it("cancel closes the form and clears what was typed", async () => {
    const onAdd = vi.fn();
    render(<NewCardForm onAdd={onAdd} />);

    await openForm();
    await userEvent.type(screen.getByPlaceholderText(/card title/i), "Discarded");
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(onAdd).not.toHaveBeenCalled();
    // Reopening shows an empty title, proving the draft was reset.
    await openForm();
    expect(screen.getByPlaceholderText(/card title/i)).toHaveValue("");
  });
});
