// Thin client for the FastAPI backend. The static site is served from the same
// origin as the API, so relative URLs and cookie credentials work directly.

export type Me = { username: string };

export async function getMe(): Promise<Me> {
  const response = await fetch("/api/me", { credentials: "include" });
  if (!response.ok) {
    throw new Error("Not authenticated");
  }
  return response.json();
}

export async function login(username: string, password: string): Promise<Me> {
  const response = await fetch("/api/login", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error("Invalid credentials");
  }
  return response.json();
}

export async function logout(): Promise<void> {
  await fetch("/api/logout", { method: "POST", credentials: "include" });
}
