import axios from "axios";
import type { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from "axios";

import type { ApiError, PaginatedResponse } from "@/types";

const apiClient: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem("auth_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export async function getPaginated<T>(
  url: string,
  params?: Record<string, unknown>,
): Promise<PaginatedResponse<T>> {
  const response = await apiClient.get<PaginatedResponse<T>>(url, { params });
  return response.data;
}

export async function getById<T>(
  url: string,
  id: string,
): Promise<T> {
  const response = await apiClient.get<T>(`${url}/${id}`);
  return response.data;
}

export async function create<T>(
  url: string,
  data: Partial<T>,
): Promise<T> {
  const response = await apiClient.post<T>(url, data);
  return response.data;
}

export async function update<T>(
  url: string,
  id: string,
  data: Partial<T>,
): Promise<T> {
  const response = await apiClient.put<T>(`${url}/${id}`, data);
  return response.data;
}

export async function remove(
  url: string,
  id: string,
): Promise<void> {
  await apiClient.delete(`${url}/${id}`);
}

export default apiClient;
