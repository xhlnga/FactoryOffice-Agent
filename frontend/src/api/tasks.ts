import { apiGet, apiPost, type ApiListResponse } from './http'
import type { ApprovalItem } from './approvals'
import type { Priority } from './workflows'

export type TaskStatus = 'todo' | 'in_progress' | 'done' | 'cancelled'

export type TaskItem = {
  id: number
  title: string
  description: string
  assignee?: string | null
  due_date?: string | null
  priority: Priority
  status: TaskStatus
  source?: string | null
  created_at: string
}

export type TaskCreateRequest = {
  title: string
  description?: string
  assignee?: string | null
  due_date?: string | null
  priority?: Priority
  source?: string | null
}

export type TaskCreateResponse = {
  approval: ApprovalItem
  requires_approval: boolean
  message: string
}

export type TaskDetailResponse = {
  task: TaskItem
  message: string
}

export function listTasks() {
  return apiGet<ApiListResponse<TaskItem>>('/tasks')
}

// 创建任务会先生成审批记录，批准后才写入正式任务表。
export function createTask(payload: TaskCreateRequest) {
  return apiPost<TaskCreateResponse, TaskCreateRequest>('/tasks', payload)
}

export function getTask(taskId: number) {
  return apiGet<TaskDetailResponse>(`/tasks/${taskId}`)
}
