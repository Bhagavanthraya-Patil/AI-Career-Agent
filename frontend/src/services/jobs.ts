import type { Job, PaginatedResponse } from "@/types";
import apiClient from "@/services/api";

export interface JobSearchParams {
  q?: string;
  page?: number;
  page_size?: number;
  location?: string;
  remote_type?: string;
  employment_type?: string;
  experience_level?: string;
  status?: string;
  source?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export async function getJobs(
  params?: JobSearchParams,
): Promise<PaginatedResponse<Job>> {
  const response = await apiClient.get<PaginatedResponse<Job>>("/jobs", {
    params,
  });
  return response.data;
}

export async function getJob(id: string): Promise<Job> {
  const response = await apiClient.get<Job>(`/jobs/${id}`);
  return response.data;
}

export async function searchJobs(
  q: string,
  params?: Omit<JobSearchParams, "q">,
): Promise<PaginatedResponse<Job>> {
  const response = await apiClient.get<PaginatedResponse<Job>>("/jobs/search", {
    params: { q, ...params },
  });
  return response.data;
}
