import { create } from "zustand";

export interface JobsFilters {
  q: string;
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: "asc" | "desc";
  remote_type: string;
  employment_type: string;
  experience_level: string;
  salary_min: number | null;
  salary_max: number | null;
  location: string;
  company: string;
  source: string;
  status: string;
}

const defaultFilters: JobsFilters = {
  q: "",
  page: 1,
  page_size: 20,
  sort_by: "scraped_at",
  sort_order: "desc",
  remote_type: "",
  employment_type: "",
  experience_level: "",
  salary_min: null,
  salary_max: null,
  location: "",
  company: "",
  source: "",
  status: "",
};

interface JobsStore {
  filters: JobsFilters;
  selectedJobId: string | null;
  setFilter: <K extends keyof JobsFilters>(key: K, value: JobsFilters[K]) => void;
  setFilters: (filters: Partial<JobsFilters>) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  selectJob: (id: string | null) => void;
  setSort: (sort_by: string, sort_order?: "asc" | "desc") => void;
}

export const useJobsStore = create<JobsStore>()((set) => ({
  filters: { ...defaultFilters },
  selectedJobId: null,
  setFilter: (key, value) =>
    set((state) => ({
      filters: { ...state.filters, [key]: value, page: key === "page" ? value : 1 },
    })),
  setFilters: (partial) =>
    set((state) => ({
      filters: { ...state.filters, ...partial, page: 1 },
    })),
  resetFilters: () =>
    set({
      filters: { ...defaultFilters },
      selectedJobId: null,
    }),
  setPage: (page) =>
    set((state) => ({
      filters: { ...state.filters, page },
    })),
  selectJob: (id) => set({ selectedJobId: id }),
  setSort: (sort_by, sort_order) =>
    set((state) => ({
      filters: { ...state.filters, sort_by, sort_order: sort_order ?? state.filters.sort_order, page: 1 },
    })),
}));
