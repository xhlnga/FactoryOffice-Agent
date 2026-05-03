import { apiPost } from './http'

export type Citation = {
  document_id?: number | null
  document_title?: string | null
  filename?: string | null
  chunk_id?: number | null
  chunk_index?: number | null
  score?: number | null
}

export type KnowledgeSearchRequest = {
  query: string
  top_k?: number
}

export type KnowledgeSearchResult = Citation & {
  chunk_text: string
}

export type KnowledgeSearchResponse = {
  query: string
  top_k: number
  results: KnowledgeSearchResult[]
  message: string
}

export type KnowledgeAskRequest = {
  question: string
  top_k?: number
}

export type KnowledgeAskResponse = {
  question: string
  answer: string
  citations: Citation[]
  message?: string | null
}

export function searchKnowledge(payload: KnowledgeSearchRequest) {
  return apiPost<KnowledgeSearchResponse, KnowledgeSearchRequest>('/knowledge/search', payload)
}

export function askKnowledge(payload: KnowledgeAskRequest) {
  return apiPost<KnowledgeAskResponse, KnowledgeAskRequest>('/knowledge/ask', payload)
}
