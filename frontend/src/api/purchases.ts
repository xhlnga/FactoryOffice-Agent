import { apiGet, apiPost, type ApiListResponse } from './http'
import type { ApprovalItem } from './approvals'

export type PurchaseStatus = 'draft' | 'pending_approval' | 'approved' | 'rejected'

export type PurchaseItem = {
  id: number
  item_name: string
  quantity: number
  reason: string
  budget?: number | null
  supplier?: string | null
  status: PurchaseStatus
  created_by?: number | null
  created_at: string
}

export type PurchaseCreateRequest = {
  item_name: string
  quantity: number
  reason?: string
  budget?: number | null
  supplier?: string | null
  created_by?: number | null
}

export type PurchaseCreateResponse = {
  approval: ApprovalItem
  requires_approval: boolean
  message: string
}

export type PurchaseDetailResponse = {
  purchase_request: PurchaseItem
  message: string
}

export function listPurchases() {
  return apiGet<ApiListResponse<PurchaseItem>>('/purchases')
}

// 采购申请不能绕过审批，前端展示时应把它当作“申请草稿/待审批动作”。
export function createPurchase(payload: PurchaseCreateRequest) {
  return apiPost<PurchaseCreateResponse, PurchaseCreateRequest>('/purchases', payload)
}

export function getPurchase(purchaseId: number) {
  return apiGet<PurchaseDetailResponse>(`/purchases/${purchaseId}`)
}
