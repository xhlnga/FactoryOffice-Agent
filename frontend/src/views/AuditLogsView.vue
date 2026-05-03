<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { listAuditLogs, type AuditLogItem } from '../api/auditLogs'

const logs = ref<AuditLogItem[]>([])
const total = ref(0)
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

const filters = reactive({
  user_id: undefined as number | string | undefined,
  action: '',
  limit: 50 as number | string,
})

async function loadLogs() {
  loading.value = true
  errorMessage.value = ''

  const userId = filters.user_id == null || filters.user_id === '' ? undefined : Number(filters.user_id)
  const limit = Number(filters.limit)

  if (userId !== undefined && (!Number.isInteger(userId) || userId < 1)) {
    errorMessage.value = '用户 ID 必须是大于 0 的整数。'
    loading.value = false
    return
  }

  if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
    errorMessage.value = '日志条数必须在 1 到 200 之间。'
    loading.value = false
    return
  }

  try {
    const response = await listAuditLogs({
      user_id: userId,
      action: filters.action || undefined,
      limit,
    })
    logs.value = response.items
    total.value = response.total
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '审计日志加载失败。'
  } finally {
    loading.value = false
  }
}

function formatArgs(args?: Record<string, unknown> | null) {
  return args ? JSON.stringify(args, null, 2) : '-'
}

function formatText(value?: string | null) {
  return value?.trim() || '-'
}

onMounted(loadLogs)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>审计日志</h3>
        <p>记录用户输入、模型输出、工具参数、审批决定和执行结果。</p>
      </div>
      <button type="button" @click="loadLogs">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>查询条件</h4>
      <div class="form-row">
        <label>用户 ID<input v-model.number="filters.user_id" type="number" min="1" /></label>
        <label>动作<input v-model="filters.action" placeholder="例如 create_task" /></label>
        <label>条数<input v-model.number="filters.limit" type="number" min="1" max="200" /></label>
        <button type="button" @click="loadLogs">查询</button>
      </div>
    </section>

    <section class="plain-section">
      <h4>日志列表（{{ total }}）</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>动作</th>
            <th>用户</th>
            <th>工具</th>
            <th>参数</th>
            <th>输入</th>
            <th>输出/结果</th>
            <th>状态</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td>{{ log.action }}</td>
            <td>{{ log.user_id || '-' }}</td>
            <td>{{ log.tool_name || '-' }}</td>
            <td class="mono-cell"><pre class="json-pre">{{ formatArgs(log.tool_args) }}</pre></td>
            <td class="mono-cell"><pre class="json-pre">{{ formatText(log.input) }}</pre></td>
            <td class="mono-cell"><pre class="json-pre">{{ formatText(log.output) }}</pre></td>
            <td>{{ log.status }}</td>
            <td>{{ log.created_at }}</td>
          </tr>
          <tr v-if="logs.length === 0">
            <td colspan="8" class="empty-cell">暂无审计日志。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
