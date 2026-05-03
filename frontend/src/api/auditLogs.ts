import { apiGet, type ApiListResponse } from './http'

export type AuditStatus = 'success' | 'failed' | 'pending'

export type AuditLogItem = {
  id: number
  user_id?: number | null
  action: string
  input?: string | null
  output?: string | null
  tool_name?: string | null
  tool_args?: Record<string, unknown> | null
  status: AuditStatus
  created_at: string
}

export type AuditLogQuery = {
  user_id?: number
  action?: string
  limit?: number
}

export type AuditLogDetailResponse = {
  audit_log: AuditLogItem
  message: string
}

const managerRoleConfig = {
  headers: {
    'X-User-Role': 'manager',
  },
}

export function listAuditLogs(params: AuditLogQuery = {}) {
  return apiGet<ApiListResponse<AuditLogItem> & { filters: AuditLogQuery }>('/audit-logs', {
    ...managerRoleConfig,
    params,
  })
}

export function getAuditLog(logId: number) {
  return apiGet<AuditLogDetailResponse>(`/audit-logs/${logId}`, managerRoleConfig)
}
