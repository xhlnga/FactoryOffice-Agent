import { apiDelete, apiGet, apiPost, type ApiListResponse } from './http'

export type DocumentItem = {
  id: number
  filename: string
  title: string
  category: string
  content_type?: string | null
  file_size_bytes?: number | null
  file_sha256?: string | null
  uploaded_by?: number | null
  deleted_at?: string | null
  created_at: string
}

export type DocumentUploadResponse = {
  document: DocumentItem
  status: string
  chunk_count?: number
  message: string
}

export type DocumentDeleteApprovalResponse = {
  document_id: number
  approval_id: number
  status: string
  message: string
}

export function listDocuments() {
  return apiGet<ApiListResponse<DocumentItem>>('/documents')
}

export function uploadDocument(file: File, category = '未分类') {
  const formData = new FormData()
  formData.append('file', file)

  return apiPost<DocumentUploadResponse, FormData>('/documents/upload', formData, {
    params: { category },
  })
}

const managerRoleConfig = {
  headers: {
    'X-User-Role': 'manager',
  },
}

// 删除文档属于高风险动作：后端只创建审批记录，不会直接删除。
export function requestDeleteDocument(documentId: number) {
  return apiDelete<DocumentDeleteApprovalResponse>(`/documents/${documentId}`, managerRoleConfig)
}
