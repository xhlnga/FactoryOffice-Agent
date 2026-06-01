import { apiGet, apiPost, type ApiListResponse } from './http'

export type ApprovalStepMode = 'any' | 'all'
export type ApproverType = 'user' | 'role' | 'department_manager' | 'expression'
export type ApprovalTemplateStatus = 'enabled' | 'disabled'

export type ApprovalTemplateStep = {
  id: number
  template_id: number
  step_order: number
  name: string
  approver_type: ApproverType
  approver_value: string
  mode: ApprovalStepMode
  timeout_hours?: number | null
  escalate_to?: string | null
  created_at: string
}

export type ApprovalTemplate = {
  id: number
  enterprise_id?: number | null
  name: string
  business_type: string
  description?: string | null
  min_amount?: number | null
  max_amount?: number | null
  status: ApprovalTemplateStatus
  is_default: boolean
  steps: ApprovalTemplateStep[]
  created_at: string
}

export type ApprovalTemplateCreatePayload = {
  enterprise_id?: number
  name: string
  business_type: string
  description?: string
  min_amount?: number | null
  max_amount?: number | null
  is_default?: boolean
  steps: Array<{
    step_order: number
    name: string
    approver_type: ApproverType
    approver_value: string
    mode?: ApprovalStepMode
    timeout_hours?: number | null
    escalate_to?: string | null
  }>
}

const adminRoleConfig = {
  headers: {
    'X-User-Role': 'admin',
  },
}

const managerRoleConfig = {
  headers: {
    'X-User-Role': 'manager',
  },
}

export function listApprovalTemplates() {
  return apiGet<ApiListResponse<ApprovalTemplate>>('/approval-templates', managerRoleConfig)
}

export function createApprovalTemplate(payload: ApprovalTemplateCreatePayload) {
  return apiPost<{ template: ApprovalTemplate; message: string }, ApprovalTemplateCreatePayload>(
    '/approval-templates',
    payload,
    adminRoleConfig,
  )
}
