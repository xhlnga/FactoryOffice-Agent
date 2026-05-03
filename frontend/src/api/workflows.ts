import { apiPost } from './http'

export type Priority = 'low' | 'medium' | 'high' | 'urgent'

export type TextWorkflowRequest = {
  content: string
}

export type TaskDraft = {
  title: string
  assignee?: string | null
  due_date?: string | null
  priority: Priority
  description: string
}

export type TicketDraft = {
  ticket_type: string
  title: string
  description: string
  priority: Priority
  suggested_action?: string | null
}

export type QualityIssueTicketDraft = {
  ticket_type: string
  title: string
  description: string
  priority: Priority
  abnormality_type: string
  affected_scope: string
  initial_disposition: string
  required_actions: string[]
}

export type PurchaseDraft = {
  item_name?: string | null
  quantity?: number | null
  reason?: string | null
  budget?: number | null
  supplier?: string | null
}

export type WeeklyReportDraft = {
  progress: string
  issues: string
  quality_risks: string
  equipment_risks: string
  purchase_risks: string
  next_plan: string
  decisions_needed: string
}

export type MeetingToTasksResponse = {
  source: string
  tasks: TaskDraft[]
  workflow_status: string
  requires_approval: boolean
  message: string
}

export type MaintenanceTicketResponse = {
  source: string
  ticket_draft?: TicketDraft | null
  workflow_status: string
  requires_approval: boolean
  message: string
}

export type QualityIssueResponse = {
  source: string
  quality_issue_draft?: QualityIssueTicketDraft | null
  workflow_status: string
  requires_approval: boolean
  message: string
}

export type PurchaseWorkflowResponse = {
  source: string
  purchase_draft?: PurchaseDraft | null
  missing_fields: string[]
  workflow_status: string
  requires_approval: boolean
  message: string
}

export type WeeklyReportResponse = {
  source: string
  weekly_report?: WeeklyReportDraft | null
  message: string
}

export function generateMeetingTasks(content: string) {
  return apiPost<MeetingToTasksResponse, TextWorkflowRequest>('/workflows/meeting-to-tasks', { content })
}

export function generateMaintenanceTicket(content: string) {
  return apiPost<MaintenanceTicketResponse, TextWorkflowRequest>('/workflows/maintenance-ticket', { content })
}

export function generateQualityIssue(content: string) {
  return apiPost<QualityIssueResponse, TextWorkflowRequest>('/workflows/quality-issue', { content })
}

export function generatePurchaseRequest(content: string) {
  return apiPost<PurchaseWorkflowResponse, TextWorkflowRequest>('/workflows/purchase-request', { content })
}

export function generateWeeklyReport(content: string) {
  return apiPost<WeeklyReportResponse, TextWorkflowRequest>('/workflows/weekly-report', { content })
}
