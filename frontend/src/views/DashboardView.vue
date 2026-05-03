<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { listAuditLogs, type AuditLogItem } from '../api/auditLogs'
import { listPendingApprovals } from '../api/approvals'
import { listDocuments } from '../api/documents'
import { listPurchases } from '../api/purchases'
import { listTasks } from '../api/tasks'
import { listTickets } from '../api/tickets'

const loading = ref(false)
const errorMessage = ref('')
const documentTotal = ref(0)
const taskTotal = ref(0)
const ticketTotal = ref(0)
const purchaseTotal = ref(0)
const pendingApprovalTotal = ref(0)
const recentLogs = ref<AuditLogItem[]>([])

const metrics = computed(() => [
  { label: '知识库文档', value: documentTotal.value },
  { label: '任务', value: taskTotal.value },
  { label: '工单', value: ticketTotal.value },
  { label: '采购申请', value: purchaseTotal.value },
  { label: '待审批', value: pendingApprovalTotal.value },
])

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [documents, tasks, tickets, purchases, approvals, logs] = await Promise.all([
      listDocuments(),
      listTasks(),
      listTickets(),
      listPurchases(),
      listPendingApprovals(),
      listAuditLogs({ limit: 5 }),
    ])

    documentTotal.value = documents.total
    taskTotal.value = tasks.total
    ticketTotal.value = tickets.total
    purchaseTotal.value = purchases.total
    pendingApprovalTotal.value = approvals.total
    recentLogs.value = logs.items
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '仪表盘数据加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>首页仪表盘</h3>
        <p>集中查看知识库、流程对象、待审批动作和最近审计记录。</p>
      </div>
      <button type="button" @click="loadDashboard">刷新</button>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="loading" class="muted-text">正在加载仪表盘数据...</p>

    <div class="metric-grid">
      <article v-for="metric in metrics" :key="metric.label" class="metric-card">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </article>
    </div>

    <section class="plain-section">
      <h4>最近审计记录</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>动作</th>
            <th>工具</th>
            <th>状态</th>
            <th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in recentLogs" :key="log.id">
            <td>{{ log.action }}</td>
            <td>{{ log.tool_name || '-' }}</td>
            <td>{{ log.status }}</td>
            <td>{{ log.created_at }}</td>
          </tr>
          <tr v-if="recentLogs.length === 0">
            <td colspan="4" class="empty-cell">暂无审计记录。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
