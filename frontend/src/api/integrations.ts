import { apiGet, apiPost, type ApiListResponse } from './http'

export type IntegrationPlatform =
  | 'local'
  | 'generic_webhook'
  | 'wecom'
  | 'dingtalk'
  | 'feishu'
  | 'generic_oa'
  | 'generic_erp'
  | 'generic_mes'
  | 'generic_wms'

export type IntegrationStatus = 'active' | 'disabled'

export type IntegrationConfig = {
  id: number
  enterprise_id: number
  platform: IntegrationPlatform
  name: string
  status: IntegrationStatus
  corp_id?: string | null
  app_key?: string | null
  agent_id?: string | null
  webhook_url?: string | null
  callback_url?: string | null
  encrypted_config: Record<string, unknown>
  last_health_status?: string | null
  created_at: string
}

export type IntegrationConfigPayload = {
  enterprise_id?: number
  platform: IntegrationPlatform
  name?: string
  corp_id?: string | null
  app_key?: string | null
  agent_id?: string | null
  webhook_url?: string | null
  callback_url?: string | null
  encrypted_config?: Record<string, unknown>
  enabled?: boolean
}

export type NotificationDelivery = {
  id: number
  platform: IntegrationPlatform
  message_type: string
  title?: string | null
  business_type?: string | null
  business_id?: string | null
  status: 'pending' | 'success' | 'failed' | 'retrying'
  response_code?: number | null
  retryable: boolean
  retry_count: number
  last_error?: string | null
  delivered_at?: string | null
  created_at: string
}

export type IntegrationTestResponse = {
  success: boolean
  message: string
  delivery_id?: number | null
  response_code?: number | null
  response_body?: string | null
  error_message?: string | null
}

const adminRoleConfig = {
  headers: {
    'X-User-Role': 'admin',
  },
}

export function listIntegrations() {
  return apiGet<ApiListResponse<IntegrationConfig>>('/integrations', adminRoleConfig)
}

export function createIntegration(payload: IntegrationConfigPayload) {
  return apiPost<{ config: IntegrationConfig; message: string }, IntegrationConfigPayload>(
    '/integrations',
    payload,
    adminRoleConfig,
  )
}

export function enableIntegration(configId: number) {
  return apiPost<{ config: IntegrationConfig; message: string }>(
    `/integrations/${configId}/enable`,
    undefined,
    adminRoleConfig,
  )
}

export function disableIntegration(configId: number) {
  return apiPost<{ config: IntegrationConfig; message: string }>(
    `/integrations/${configId}/disable`,
    undefined,
    adminRoleConfig,
  )
}

export function testIntegration(configId: number) {
  return apiPost<IntegrationTestResponse>(
    `/integrations/${configId}/test`,
    {
      title: 'FactoryOffice-Agent 集成测试',
      content: '这是一条企业集成测试通知。',
    },
    adminRoleConfig,
  )
}

export function listNotificationDeliveries() {
  return apiGet<ApiListResponse<NotificationDelivery>>('/integrations/deliveries', adminRoleConfig)
}

export function previewOrgSync(configId: number) {
  return apiPost<{ preview: Record<string, unknown>; message: string }>(
    `/integrations/${configId}/org/preview`,
    undefined,
    adminRoleConfig,
  )
}

export function runOrgSync(configId: number) {
  return apiPost<{ result: Record<string, unknown>; message: string }>(
    `/integrations/${configId}/org/sync`,
    undefined,
    adminRoleConfig,
  )
}
