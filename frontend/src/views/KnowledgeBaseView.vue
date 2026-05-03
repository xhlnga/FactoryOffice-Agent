<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  listDocuments,
  requestDeleteDocument,
  uploadDocument,
  type DocumentItem,
} from '../api/documents'
import {
  askKnowledge,
  searchKnowledge,
  type Citation,
  type KnowledgeSearchResult,
} from '../api/knowledge'

const documents = ref<DocumentItem[]>([])
const total = ref(0)
const loading = ref(false)
const selectedFile = ref<File | null>(null)
const category = ref('制度')
const question = ref('采购超过 5 万怎么审批？')
const answer = ref('')
const citations = ref<Citation[]>([])
const searchResults = ref<KnowledgeSearchResult[]>([])
const message = ref('')
const errorMessage = ref('')

async function loadDocuments() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listDocuments()
    documents.value = response.items
    total.value = response.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档列表加载失败。'
  } finally {
    loading.value = false
  }
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  selectedFile.value = input.files?.[0] || null
}

async function handleUpload() {
  if (!selectedFile.value) {
    errorMessage.value = '请先选择要上传的文档。'
    return
  }

  loading.value = true
  message.value = ''
  errorMessage.value = ''

  try {
    const response = await uploadDocument(selectedFile.value, category.value)
    message.value = response.chunk_count == null
      ? response.message
      : `${response.message} 可直接用于知识库检索。`
    selectedFile.value = null
    await loadDocuments()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '文档上传失败。'
  } finally {
    loading.value = false
  }
}

async function handleAsk() {
  if (!question.value.trim()) {
    errorMessage.value = '请输入知识库问题。'
    return
  }

  loading.value = true
  answer.value = ''
  citations.value = []
  searchResults.value = []
  errorMessage.value = ''

  try {
    const response = await askKnowledge({ question: question.value, top_k: 5 })
    answer.value = response.answer
    citations.value = response.citations
    message.value = response.message || ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库问答失败。'
  } finally {
    loading.value = false
  }
}

async function handleSearch() {
  if (!question.value.trim()) {
    errorMessage.value = '请输入检索问题。'
    return
  }

  loading.value = true
  searchResults.value = []
  errorMessage.value = ''

  try {
    const response = await searchKnowledge({ query: question.value, top_k: 5 })
    searchResults.value = response.results
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库检索失败。'
  } finally {
    loading.value = false
  }
}

async function handleDelete(documentId: number) {
  loading.value = true
  message.value = ''
  errorMessage.value = ''

  try {
    const response = await requestDeleteDocument(documentId)
    message.value = `${response.message} 审批单号：${response.approval_id}`
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '删除审批创建失败。'
  } finally {
    loading.value = false
  }
}

function formatBytes(value?: number | null) {
  if (!value) {
    return '0 B'
  }
  if (value < 1024) {
    return `${value} B`
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function formatScore(score?: number | null) {
  return score == null ? '-' : score.toFixed(3)
}

onMounted(loadDocuments)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>知识库</h3>
        <p>上传企业文档，进行知识库检索和带来源的问答。</p>
      </div>
      <button type="button" @click="loadDocuments">刷新文档</button>
    </div>

    <p v-if="message" class="success-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="loading" class="muted-text">正在处理...</p>

    <section class="plain-section">
      <h4>上传文档</h4>
      <div class="form-row">
        <label>
          文档分类
          <select v-model="category">
            <option>制度</option>
            <option>设备手册</option>
            <option>质量流程</option>
            <option>采购流程</option>
            <option>安全规范</option>
            <option>项目文档</option>
          </select>
        </label>
        <label>
          选择文件
          <input type="file" accept=".pdf,.docx,.txt,.md,.markdown" @change="handleFileChange" />
        </label>
        <button type="button" @click="handleUpload">上传</button>
      </div>
    </section>

    <section class="plain-section">
      <h4>文档列表（{{ total }}）</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>标题</th>
            <th>分类</th>
            <th>文件名</th>
            <th>大小</th>
            <th>动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="document in documents" :key="document.id">
            <td>{{ document.title }}</td>
            <td>{{ document.category }}</td>
            <td>{{ document.filename }}</td>
            <td>{{ formatBytes(document.file_size_bytes) }}</td>
            <td>
              <button type="button" class="text-button" @click="handleDelete(document.id)">
                申请删除
              </button>
            </td>
          </tr>
          <tr v-if="documents.length === 0">
            <td colspan="5" class="empty-cell">暂无文档。</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="plain-section">
      <h4>知识库问答</h4>
      <textarea v-model="question" rows="4" placeholder="输入要查询的制度、SOP、设备或流程问题" />
      <div class="action-row">
        <button type="button" @click="handleAsk">问答</button>
        <button type="button" class="secondary-button" @click="handleSearch">只检索片段</button>
      </div>

      <div v-if="answer" class="result-box">
        <strong>回答</strong>
        <p>{{ answer }}</p>
      </div>

      <div v-if="citations.length > 0" class="result-box">
        <strong>引用来源</strong>
        <ul>
          <li v-for="citation in citations" :key="`${citation.document_id}-${citation.chunk_id}`">
            {{ citation.document_title || citation.filename || '未命名文档' }}
            <span v-if="citation.chunk_index != null">，chunk {{ citation.chunk_index }}</span>
            <span v-if="citation.score != null">，相关度 {{ formatScore(citation.score) }}</span>
          </li>
        </ul>
      </div>

      <div v-if="searchResults.length > 0" class="result-box">
        <strong>检索片段</strong>
        <ol>
          <li v-for="result in searchResults" :key="`${result.document_id}-${result.chunk_id}`">
            <strong>{{ result.document_title || result.filename || '未命名文档' }}</strong>
            <span v-if="result.chunk_index != null">，chunk {{ result.chunk_index }}</span>
            <span v-if="result.score != null">，相关度 {{ formatScore(result.score) }}</span>
            <br />
            {{ result.chunk_text }}
          </li>
        </ol>
      </div>
    </section>
  </section>
</template>
