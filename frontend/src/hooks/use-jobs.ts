import { useState, useEffect, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { Job, PaginatedResponse } from "@/types";
import apiClient from "@/services/api";
import { useJobsStore } from "@/store/jobs-store";

export function useJobs() {
  const { filters, setFilter, setFilters, resetFilters, setPage, selectJob, selectedJobId, setSort } =
    useJobsStore();

  const queryKey = useMemo(() => ["jobs", filters], [filters]);

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey,
    queryFn: async () => {
      const params: Record<string, unknown> = {};
      if (filters.q) params.q = filters.q;
      if (filters.page) params.page = filters.page;
      if (filters.page_size) params.page_size = filters.page_size;
      if (filters.sort_by) params.sort_by = filters.sort_by;
      if (filters.sort_order) params.sort_order = filters.sort_order;
      if (filters.remote_type) params.remote_type = filters.remote_type;
      if (filters.employment_type) params.employment_type = filters.employment_type;
      if (filters.experience_level) params.experience_level = filters.experience_level;
      if (filters.salary_min !== null) params.salary_min = filters.salary_min;
      if (filters.salary_max !== null) params.salary_max = filters.salary_max;
      if (filters.location) params.location = filters.location;
      if (filters.company) params.company = filters.company;
      if (filters.source) params.source = filters.source;
      if (filters.status) params.status = filters.status;
      const res = await apiClient.get<PaginatedResponse<Job>>("/jobs", { params });
      return res.data;
    },
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });

  return {
    jobs: data?.items ?? [],
    total: data?.total ?? 0,
    totalPages: data?.total_pages ?? 0,
    currentPage: filters.page,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
    filters,
    setFilter,
    setFilters,
    resetFilters,
    setPage,
    setSort,
    selectJob,
    selectedJobId,
  };
}

export function useJob(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => {
      const res = await apiClient.get<Job>(`/jobs/${jobId}`);
      return res.data;
    },
    enabled: !!jobId,
    staleTime: 60_000,
  });
}

export function useRefreshJobs() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiClient.post<{ message: string }>("/jobs/refresh");
      return res.data;
    },
    onSuccess: () => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["jobs"] });
      }, 5000);
    },
  });
}

export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debouncedValue;
}
