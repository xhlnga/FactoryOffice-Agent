<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { createTask, listTasks, type TaskItem } from '../api/tasks'
import type { Priority } from '../api/workflows'

const tasks = ref<TaskItem[]>([])
const total = ref(0)
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

const form = reactive({
  title: '',
  description: '',
  assignee: '',
  due_date: '',
  priority: 'medium' as Priority,
  source: 'manual',
})

async function loadTasks() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listTasks()
    tasks.value = response.items
    total.value = response.total
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '任务列表加载失败。'
  } finally {
    loading.value = false
  }
}

async function submitTask() {
  if (!form.title.trim()) {
    errorMessage.value = '任务标题不能为空。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await createTask({
      title: form.title,
      description: form.description,
      assignee: form.assignee || null,
      due_date: form.due_date || null,
      priority: form.priority,
      source: form.source,
    })
    message.value = `${response.message} 审批单号：${response.approval.id}`
    await loadTasks()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '任务创建失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadTasks)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>任务管理</h3>
        <p>查看任务列表，并保留人工创建任务的入口；批量任务应从会议流程生成并确认。</p>
      </div>
      <button type="button" @click="loadTasks">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>创建任务</h4>
      <div class="form-grid">
        <label>标题<input v-model="form.title" /></label>
        <label>负责人<input v-model="form.assignee" /></label>
        <label>截止日期<input v-model="form.due_date" type="date" /></label>
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
        <button type="button" :disabled="loading" @click="submitTask">提交</button>
      </div>
    </section>

    <section class="plain-section">
      <h4>任务列表（{{ total }}）</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>标题</th>
            <th>负责人</th>
            <th>截止日期</th>
            <th>优先级</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.id">
            <td>{{ task.title }}</td>
            <td>{{ task.assignee || '-' }}</td>
            <td>{{ task.due_date || '-' }}</td>
            <td>{{ task.priority }}</td>
            <td>{{ task.status }}</td>
          </tr>
          <tr v-if="tasks.length === 0">
            <td colspan="5" class="empty-cell">暂无任务。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
