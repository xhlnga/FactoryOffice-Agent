import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'

export type ApiListResponse<T> = {
  items: T[]
  total: number
  message: string
}

export class ApiError extends Error {
  status?: number
  details?: unknown

  constructor(message: string, status?: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

const apiBaseURL = import.meta.env.VITE_API_BASE_URL || '/api'

export const http = axios.create({
  baseURL: apiBaseURL,
  timeout: 30_000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('factoryoffice_access_token')

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => Promise.reject(normalizeApiError(error)),
)

export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await http.get<T>(url, config)
  return response.data
}

export async function apiPost<T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> {
  const response = await http.post<T>(url, body, config)
  return response.data
}

export async function apiDelete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await http.delete<T>(url, config)
  return response.data
}

function normalizeApiError(error: AxiosError): ApiError {
  const status = error.response?.status
  const data = error.response?.data
  const message = resolveErrorMessage(data) || error.message || '请求失败，请稍后重试。'

  return new ApiError(message, status, data)
}

function resolveErrorMessage(data: unknown): string | undefined {
  if (!data || typeof data !== 'object') {
    return undefined
  }

  if ('message' in data && typeof data.message === 'string') {
    return data.message
  }

  if ('detail' in data && typeof data.detail === 'string') {
    return data.detail
  }

  return undefined
}
