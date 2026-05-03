import { apiPost } from './http'

export type AgentChatRequest = {
  message: string
  user_id?: number | null
  context?: Record<string, unknown>
}

export type ToolCallPreview = {
  tool_name: string
  tool_args: Record<string, unknown>
  requires_approval: boolean
}

export type MissingField = {
  name: string
  label: string
  question: string
}

export type AgentTraceStep = {
  step: string
  status: string
  detail: Record<string, unknown>
}

export type AgentChatResponse = {
  message: string
  intent: string
  sop_id?: string | null
  sop_name?: string | null
  task_status?: string | null
  answer: string
  slot_values: Record<string, unknown>
  missing_fields: MissingField[]
  next_question?: string | null
  tool_calls: ToolCallPreview[]
  requires_approval: boolean
  trace: AgentTraceStep[]
}

export function chatWithAgent(payload: AgentChatRequest) {
  return apiPost<AgentChatResponse, AgentChatRequest>('/agent/chat', payload)
}
