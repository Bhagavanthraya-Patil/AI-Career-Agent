import { create } from "zustand";
import type { User } from "@/types";
import { api } from "@/lib/api";

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  clearUser: () => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  clearUser: () => set({ user: null, isAuthenticated: false }),
  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const { data } = await api.post<{ user: User; access_token: string }>("/auth/login", {
        email,
        password,
      });
      localStorage.setItem("access_token", data.access_token);
      set({ user: data.user, isAuthenticated: true, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },
  logout: async () => {
    localStorage.removeItem("access_token");
    delete api.defaults.headers.common["Authorization"];
    set({ user: null, isAuthenticated: false });
  },
}));
