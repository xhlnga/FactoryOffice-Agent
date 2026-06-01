<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import {
  approveMobileApproval,
  getMobileApproval,
  rejectMobileApproval,
  type ApprovalItem,
} from '../api/approvals'

const route = useRoute()
const approval = ref<ApprovalItem | null>(null)
const instance = ref<Record<string, unknown> | null>(null)
const reviewer = ref('移动审批人')
const comment = ref('')
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

const approvalId = computed(() => Number(route.params.id))
const approvalToken = computed(() => {
  const value = route.query.token
  return typeof value === 'string' ? value : ''
})

async function loadApproval() {
  if (!Number.isInteger(approvalId.value) || approvalId.value <= 0) {
    errorMessage.value = '审批编号不合法。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await getMobileApproval(approvalId.value, approvalToken.value)
    approval.value = response.approval
    instance.value = response.instance || null
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '审批详情加载失败。'
  } finally {
    loading.value = false
  }
}

async function decide(decision: 'approve' | 'reject') {
  if (!approval.value) {
    return
  }
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
        ? await approveMobileApproval(approval.value.id, payload, approvalToken.value)
        : await rejectMobileApproval(approval.value.id, payload, approvalToken.value)
    approval.value = response.approval
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '审批操作失败。'
  } finally {
    loading.value = false
  }
}

function pretty(value: unknown) {
  return JSON.stringify(value, null, 2)
}

onMounted(loadApproval)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>移动审批</h3>
        <p>审批人核对 AI 生成的业务动作参数后，再决定批准或拒绝。</p>
      </div>
      <button type="button" :disabled="loading" @click="loadApproval">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section v-if="approval" class="plain-section">
      <h4>审批详情</h4>
      <div class="form-grid">
        <label>审批编号<input :value="approval.id" disabled /></label>
        <label>动作类型<input :value="approval.action_type" disabled /></label>
        <label>状态<input :value="approval.status" disabled /></label>
        <label>审批人<input v-model="reviewer" /></label>
      </div>
      <label>
        审批意见
        <textarea v-model="comment" rows="3"></textarea>
      </label>
      <h4>动作参数</h4>
      <pre class="json-pre">{{ pretty(approval.action_payload) }}</pre>
      <h4>审批实例</h4>
      <pre class="json-pre">{{ instance ? pretty(instance) : '暂无多级审批实例。' }}</pre>
      <div class="action-row">
        <button type="button" :disabled="approval.status !== 'pending' || loading" @click="decide('approve')">
          批准
        </button>
        <button type="button" class="secondary-button" :disabled="approval.status !== 'pending' || loading" @click="decide('reject')">
          拒绝
        </button>
      </div>
    </section>

    <section v-else class="plain-section">
      <p class="muted-text">暂无审批详情。</p>
    </section>
  </section>
</template>
