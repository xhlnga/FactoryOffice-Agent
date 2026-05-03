<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  approveApproval,
  listApprovals,
  listPendingApprovals,
  rejectApproval,
  type ApprovalItem,
  type ApprovalStatus,
} from '../api/approvals'

const approvals = ref<ApprovalItem[]>([])
const total = ref(0)
const statusFilter = ref<ApprovalStatus | ''>('pending')
const reviewer = ref('主管')
const comment = ref('')
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

async function loadApprovals() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = statusFilter.value
      ? await listApprovals(statusFilter.value)
      : await listApprovals()
    approvals.value = response.items
    total.value = response.total
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '审批列表加载失败。'
  } finally {
    loading.value = false
  }
}

async function loadPending() {
  statusFilter.value = 'pending'
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listPendingApprovals()
    approvals.value = response.items
    total.value = response.total
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '待审批列表加载失败。'
  } finally {
    loading.value = false
  }
}

async function decide(id: number, decision: 'approve' | 'reject') {
  if (!reviewer.value.trim()) {
    errorMessage.value = '审批人不能为空。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const payload = { reviewer: reviewer.value, comment: comment.value }
    const response =
      decision === 'approve'
        ? await approveApproval(id, payload)
        : await rejectApproval(id, payload)
    message.value = response.message
    await loadApprovals()
  } catch (error) {
    const errorText = error instanceof Error ? error.message : '审批操作失败。'
    await loadApprovals()
    errorMessage.value = errorText
  } finally {
    loading.value = false
  }
}

function formatPayload(payload: Record<string, unknown>) {
  return JSON.stringify(payload, null, 2)
}

function formatExecutionResult(result?: Record<string, unknown> | null) {
  return result ? JSON.stringify(result, null, 2) : '-'
}

onMounted(loadPending)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>审批中心</h3>
        <p>所有高风险动作先进入人工确认，批准后才执行，拒绝后不写入业务表。</p>
      </div>
      <button type="button" @click="loadApprovals">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>筛选与审批人</h4>
      <div class="form-row">
        <label>
          状态
          <select v-model="statusFilter">
            <option value="">全部</option>
            <option value="pending">待审批</option>
            <option value="approved">已批准</option>
            <option value="rejected">已拒绝</option>
            <option value="execution_failed">执行失败</option>
          </select>
        </label>
        <label>审批人<input v-model="reviewer" /></label>
        <label>审批意见<input v-model="comment" /></label>
        <button type="button" @click="loadApprovals">查询</button>
      </div>
    </section>

    <section class="plain-section">
      <h4>审批列表（{{ total }}）</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>动作类型</th>
            <th>参数</th>
            <th>状态</th>
            <th>审批人</th>
            <th>执行结果</th>
            <th>动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="approval in approvals" :key="approval.id">
            <td>{{ approval.action_type }}</td>
            <td class="mono-cell"><pre class="json-pre">{{ formatPayload(approval.action_payload) }}</pre></td>
            <td>{{ approval.status }}</td>
            <td>{{ approval.reviewer || '-' }}</td>
            <td class="mono-cell"><pre class="json-pre">{{ formatExecutionResult(approval.execution_result) }}</pre></td>
            <td>
              <div class="table-actions">
                <button
                  type="button"
                  class="text-button"
                  :disabled="approval.status !== 'pending' || loading"
                  @click="decide(approval.id, 'approve')"
                >
                  批准
                </button>
                <button
                  type="button"
                  class="text-button danger"
                  :disabled="approval.status !== 'pending' || loading"
                  @click="decide(approval.id, 'reject')"
                >
                  拒绝
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="approvals.length === 0">
            <td colspan="6" class="empty-cell">暂无审批记录。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
