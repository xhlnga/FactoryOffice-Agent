<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { createTicket, listTickets, type TicketItem } from '../api/tickets'
import type { Priority } from '../api/workflows'

const tickets = ref<TicketItem[]>([])
const total = ref(0)
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

const form = reactive({
  ticket_type: '设备维修',
  title: '',
  description: '',
  priority: 'medium' as Priority,
})

async function loadTickets() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listTickets()
    tickets.value = response.items
    total.value = response.total
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '工单列表加载失败。'
  } finally {
    loading.value = false
  }
}

async function submitTicket() {
  if (!form.title.trim()) {
    errorMessage.value = '工单标题不能为空。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await createTicket({
      ticket_type: form.ticket_type,
      title: form.title,
      description: form.description,
      priority: form.priority,
    })
    message.value = `${response.message} 审批单号：${response.approval.id}`
    await loadTickets()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '工单创建失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadTickets)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>工单管理</h3>
        <p>查看企业工单记录。当前页面新建仅开放设备维修和质量异常，正式工单应由草稿确认后写入。</p>
      </div>
      <button type="button" @click="loadTickets">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>创建工单</h4>
      <div class="form-grid">
        <label>
          工单类型
          <select v-model="form.ticket_type">
            <option>设备维修</option>
            <option>质量异常</option>
          </select>
        </label>
        <label>标题<input v-model="form.title" /></label>
        <label>
          优先级
          <select v-model="form.priority">
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
            <option value="urgent">紧急</option>
          </select>
        </label>
      </div>
      <label>描述<textarea v-model="form.description" rows="4" /></label>
      <div class="action-row">
        <button type="button" :disabled="loading" @click="submitTicket">提交</button>
      </div>
    </section>

    <section class="plain-section">
      <h4>工单列表（{{ total }}）</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>类型</th>
            <th>标题</th>
            <th>优先级</th>
            <th>状态</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ticket in tickets" :key="ticket.id">
            <td>{{ ticket.ticket_type }}</td>
            <td>{{ ticket.title }}</td>
            <td>{{ ticket.priority }}</td>
            <td>{{ ticket.status }}</td>
            <td>{{ ticket.created_at }}</td>
          </tr>
          <tr v-if="tickets.length === 0">
            <td colspan="5" class="empty-cell">暂无工单。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
