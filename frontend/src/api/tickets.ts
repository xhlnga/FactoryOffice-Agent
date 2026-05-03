import { apiGet, apiPost, type ApiListResponse } from './http'
import type { ApprovalItem } from './approvals'
import type { Priority } from './workflows'

export type TicketStatus = 'open' | 'processing' | 'resolved' | 'closed'

export type TicketItem = {
  id: number
  ticket_type: string
  title: string
  description: string
  priority: Priority
  status: TicketStatus
  created_by?: number | null
  created_at: string
}

export type TicketCreateRequest = {
  ticket_type?: string
  title: string
  description?: string
  priority?: Priority
  created_by?: number | null
}

export type TicketCreateResponse = {
  approval: ApprovalItem
  requires_approval: boolean
  message: string
}

export type TicketDetailResponse = {
  ticket: TicketItem
  message: string
}

export function listTickets() {
  return apiGet<ApiListResponse<TicketItem>>('/tickets')
}

// 正式维修工单应优先走“草稿 -> 人工确认 -> 写入”的路径。
export function createTicket(payload: TicketCreateRequest) {
  return apiPost<TicketCreateResponse, TicketCreateRequest>('/tickets', payload)
}

export function getTicket(ticketId: number) {
  return apiGet<TicketDetailResponse>(`/tickets/${ticketId}`)
}
