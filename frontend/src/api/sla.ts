import { apiGet, type ApiListResponse } from './http'

export type SLAPolicy = {
  id: number
  enterprise_id?: number | null
  business_type: string
  priority: string
  response_minutes: number
  resolve_minutes: number
  remind_before_minutes: number
  escalate_after_minutes: number
  escalate_to_role?: string | null
  enabled: boolean
  created_at: string
}

export type SLAInstance = {
  id: number
  enterprise_id?: number | null
  policy_id?: number | null
  business_type: string
  business_id: string
  status: 'active' | 'paused' | 'breached' | 'resolved' | 'cancelled'
  response_due_at?: string | null
  deadline_at?: string | null
  first_remind_at?: string | null
  breached_at?: string | null
  escalated_at?: string | null
  resolved_at?: string | null
  created_at: string
}

export type SLADefaultPolicy = {
  business_type: string
  priority: string
  response_minutes: number
  resolve_minutes: number
  remind_before_minutes: number
  escalate_after_minutes: number
  escalate_to_role: string
}

const managerRoleConfig = {
  headers: {
    'X-User-Role': 'manager',
  },
}

export function listSlaPolicies() {
  return apiGet<ApiListResponse<SLAPolicy>>('/sla/policies', managerRoleConfig)
}

export function listSlaInstances() {
  return apiGet<ApiListResponse<SLAInstance>>('/sla/instances', managerRoleConfig)
}

export function listDefaultSlaPolicies() {
  return apiGet<ApiListResponse<SLADefaultPolicy>>('/sla/default-policies', managerRoleConfig)
}
