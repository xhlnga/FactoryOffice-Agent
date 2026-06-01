import { apiGet, apiPost, type ApiListResponse } from './http'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'execution_failed'

export type ApprovalItem = {
  id: number
  action_type: string
  action_payload: Record<string, unknown>
  status: ApprovalStatus
  reviewer?: string | null
  reviewed_at?: string | null
  executed_at?: string | null
  execution_result?: Record<string, unknown> | null
  comment?: string | null
  created_at: string
}

export type ApprovalDecisionRequest = {
  reviewer: string
  comment?: string
}

export type ApprovalDecisionResponse = {
  approval: ApprovalItem
  message: string
}

export type MobileApprovalDetail = {
  approval: ApprovalItem
  instance?: Record<string, unknown> | null
  message: string
}

const managerRoleConfig = {
  headers: {
    'X-User-Role': 'manager',
  },
}

export function listApprovals(status?: ApprovalStatus) {
  return apiGet<ApiListResponse<ApprovalItem> & { status_filter?: ApprovalStatus | null }>('/approvals', {
    ...managerRoleConfig,
    params: status ? { status } : undefined,
  })
}

export function listPendingApprovals() {
  return apiGet<ApiListResponse<ApprovalItem>>('/approvals/pending', managerRoleConfig)
}

// 批准后后端会执行对应动作，并把执行结果写回审批和审计日志。
export function approveApproval(approvalId: number, payload: ApprovalDecisionRequest) {
  return apiPost<ApprovalDecisionResponse, ApprovalDecisionRequest>(
    `/approvals/${approvalId}/approve`,
    payload,
    managerRoleConfig,
  )
}

export function rejectApproval(approvalId: number, payload: ApprovalDecisionRequest) {
  return apiPost<ApprovalDecisionResponse, ApprovalDecisionRequest>(
    `/approvals/${approvalId}/reject`,
    payload,
    managerRoleConfig,
  )
}

export function getMobileApproval(approvalId: number, token?: string) {
  return apiGet<MobileApprovalDetail>(`/mobile/approvals/${approvalId}`, {
    params: token ? { token } : undefined,
  })
}

export function approveMobileApproval(approvalId: number, payload: ApprovalDecisionRequest, token?: string) {
  return apiPost<ApprovalDecisionResponse, ApprovalDecisionRequest>(
    `/mobile/approvals/${approvalId}/approve`,
    payload,
    { params: token ? { token } : undefined },
  )
}

export function rejectMobileApproval(approvalId: number, payload: ApprovalDecisionRequest, token?: string) {
  return apiPost<ApprovalDecisionResponse, ApprovalDecisionRequest>(
    `/mobile/approvals/${approvalId}/reject`,
    payload,
    { params: token ? { token } : undefined },
  )
}
