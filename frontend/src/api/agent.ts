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

export type AgentChatResponse = {
  message: string
  intent: string
  answer: string
  tool_calls: ToolCallPreview[]
  requires_approval: boolean
}

export function chatWithAgent(payload: AgentChatRequest) {
  return apiPost<AgentChatResponse, AgentChatRequest>('/agent/chat', payload)
}
