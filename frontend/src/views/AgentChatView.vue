<script setup lang="ts">
import { ref } from 'vue'

import { chatWithAgent, type AgentChatResponse } from '../api/agent'

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  result?: AgentChatResponse
}

const input = ref('采购超过 5 万怎么审批？')
const loading = ref(false)
const errorMessage = ref('')
const messages = ref<ChatMessage[]>([])

async function sendMessage() {
  const content = input.value.trim()
  if (!content) {
    errorMessage.value = '请输入要处理的问题或业务描述。'
    return
  }

  loading.value = true
  errorMessage.value = ''
  messages.value.push({ role: 'user', content })

  try {
    const response = await chatWithAgent({ message: content })
    messages.value.push({
      role: 'assistant',
      content: response.answer,
      result: response,
    })
    input.value = ''
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'AI 助手调用失败。'
  } finally {
    loading.value = false
  }
}

function formatToolArgs(args: Record<string, unknown>) {
  return JSON.stringify(args, null, 2)
}
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>AI 助手</h3>
        <p>统一处理员工提问、流程判断、工具预览和人工确认提示。</p>
      </div>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>对话</h4>
      <div class="chat-list">
        <article v-for="(message, index) in messages" :key="index" class="chat-message" :data-role="message.role">
          <strong>{{ message.role === 'user' ? '员工' : 'AI 助手' }}</strong>
          <p>{{ message.content }}</p>

          <div v-if="message.result" class="result-box compact">
            <p>意图：{{ message.result.intent }}</p>
            <p v-if="message.result.sop_name">SOP：{{ message.result.sop_name }}</p>
            <p v-if="message.result.task_status">任务状态：{{ message.result.task_status }}</p>
            <p>是否需要审批：{{ message.result.requires_approval ? '是' : '否' }}</p>
            <div v-if="message.result.missing_fields.length > 0">
              <p>缺失字段：</p>
              <ul>
                <li v-for="field in message.result.missing_fields" :key="field.name">
                  {{ field.label }}：{{ field.question }}
                </li>
              </ul>
            </div>
            <ul v-if="message.result.tool_calls.length > 0">
              <li v-for="tool in message.result.tool_calls" :key="tool.tool_name">
                {{ tool.tool_name }}，审批：{{ tool.requires_approval ? '需要' : '不需要' }}
                <pre class="json-pre">{{ formatToolArgs(tool.tool_args) }}</pre>
              </li>
            </ul>
            <details v-if="message.result.trace.length > 0">
              <summary>Agent Trace</summary>
              <ol>
                <li v-for="trace in message.result.trace" :key="`${trace.step}-${trace.status}`">
                  {{ trace.step }}：{{ trace.status }}
                  <pre class="json-pre">{{ formatToolArgs(trace.detail) }}</pre>
                </li>
              </ol>
            </details>
          </div>
        </article>
        <p v-if="messages.length === 0" class="empty-cell">暂无对话记录。</p>
      </div>

      <textarea
        v-model="input"
        rows="5"
        placeholder="例如：空压机 E07 报警，压力传感器读数异常，生产线 A 暂停。"
        @keydown.ctrl.enter="sendMessage"
      />
      <div class="action-row">
        <button type="button" :disabled="loading" @click="sendMessage">
          {{ loading ? '处理中...' : '发送' }}
        </button>
      </div>
    </section>
  </section>
</template>
