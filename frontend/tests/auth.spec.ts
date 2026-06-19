import { expect, test } from "@playwright/test";

test("gates the board behind login and supports logout", async ({ page }) => {
  await page.goto("/");

  // Unauthenticated: login screen, no board.
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toHaveCount(0);

  // Wrong credentials are rejected.
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByText(/invalid username or password/i)
  ).toBeVisible();

  // Correct credentials reveal the board.
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  // Logout returns to the login screen.
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});
