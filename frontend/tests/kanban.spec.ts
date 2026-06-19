import { expect, test } from "@playwright/test";

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("renames a column", async ({ page }) => {
  await page.goto("/");
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const title = firstColumn.getByLabel("Column title");
  await title.fill("Renamed column");
  await expect(title).toHaveValue("Renamed column");
});

test("edits a card", async ({ page }) => {
  await page.goto("/");
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn
    .getByRole("button", { name: "Edit Align roadmap themes", exact: true })
    .click();
  await firstColumn.getByLabel("Card title").fill("Edited via e2e");
  await firstColumn.getByLabel("Card details").fill("New details.");
  await firstColumn.getByRole("button", { name: /save/i }).click();
  await expect(firstColumn.getByText("Edited via e2e")).toBeVisible();
  await expect(firstColumn.getByText("Align roadmap themes")).toHaveCount(0);
});

test("deletes a card", async ({ page }) => {
  await page.goto("/");
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await expect(firstColumn.getByText("Gather customer signals")).toBeVisible();
  await firstColumn
    .getByRole("button", { name: "Delete Gather customer signals", exact: true })
    .click();
  await expect(firstColumn.getByText("Gather customer signals")).toHaveCount(0);
});

test("moves a card between columns", async ({ page }) => {
  await page.goto("/");
  const card = page.getByTestId("card-card-1");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByTestId("card-card-1")).toBeVisible();
});
