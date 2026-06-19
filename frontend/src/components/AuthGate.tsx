"use client";

import { useEffect, useState } from "react";
import { getMe, logout } from "@/lib/api";
import { KanbanBoard } from "@/components/KanbanBoard";
import { LoginForm } from "@/components/LoginForm";

type AuthStatus = "loading" | "out" | "in";

export const AuthGate = () => {
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    getMe()
      .then(() => setStatus("in"))
      .catch(() => setStatus("out"));
  }, []);

  if (status === "loading") {
    return null;
  }

  if (status === "out") {
    return <LoginForm onAuthed={() => setStatus("in")} />;
  }

  return (
    <KanbanBoard
      onLogout={async () => {
        await logout();
        setStatus("out");
      }}
    />
  );
};
