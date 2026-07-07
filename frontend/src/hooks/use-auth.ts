import { useCallback } from "react";
import { useAuthStore } from "@/store/auth-store";
import type { User } from "@/types";

interface SignupData {
  email: string;
  password: string;
  name: string;
}

export function useAuth() {
  const { user, isAuthenticated, isLoading, setUser, clearUser, login, logout } =
    useAuthStore();

  const signup = useCallback(
    async (data: SignupData) => {
      const response = await fetch("/api/v1/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      localStorage.setItem("access_token", result.access_token);
      setUser(result.user);
    },
    [setUser],
  );

  return { user, isAuthenticated, isLoading, login, logout, signup, clearUser };
}
