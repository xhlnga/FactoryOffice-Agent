<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  listDefaultSlaPolicies,
  listSlaInstances,
  listSlaPolicies,
  type SLADefaultPolicy,
  type SLAInstance,
  type SLAPolicy,
} from '../api/sla'

const policies = ref<SLAPolicy[]>([])
const defaultPolicies = ref<SLADefaultPolicy[]>([])
const instances = ref<SLAInstance[]>([])
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

async function loadSla() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [policyResponse, defaultResponse, instanceResponse] = await Promise.all([
      listSlaPolicies(),
      listDefaultSlaPolicies(),
      listSlaInstances(),
    ])
    policies.value = policyResponse.items
    defaultPolicies.value = defaultResponse.items
    instances.value = instanceResponse.items
    message.value = 'SLA 规则加载成功。'
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'SLA 规则加载失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadSla)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>SLA 设置</h3>
        <p>查看工单、质量异常和采购申请的响应时限、处理时限与升级角色。</p>
      </div>
      <button type="button" :disabled="loading" @click="loadSla">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>内置规则</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>业务类型</th>
            <th>优先级</th>
            <th>响应分钟</th>
            <th>处理分钟</th>
            <th>提前提醒</th>
            <th>升级角色</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="policy in defaultPolicies" :key="`${policy.business_type}-${policy.priority}`">
            <td>{{ policy.business_type }}</td>
            <td>{{ policy.priority }}</td>
            <td>{{ policy.response_minutes }}</td>
            <td>{{ policy.resolve_minutes }}</td>
            <td>{{ policy.remind_before_minutes }}</td>
            <td>{{ policy.escalate_to_role }}</td>
          </tr>
          <tr v-if="defaultPolicies.length === 0">
            <td colspan="6" class="empty-cell">暂无内置 SLA 规则。</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="plain-section">
      <h4>落库策略</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>业务类型</th>
            <th>优先级</th>
            <th>响应分钟</th>
            <th>处理分钟</th>
            <th>启用</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="policy in policies" :key="policy.id">
            <td>{{ policy.business_type }}</td>
            <td>{{ policy.priority }}</td>
            <td>{{ policy.response_minutes }}</td>
            <td>{{ policy.resolve_minutes }}</td>
            <td>{{ policy.enabled ? '是' : '否' }}</td>
          </tr>
          <tr v-if="policies.length === 0">
            <td colspan="5" class="empty-cell">暂无自定义 SLA 策略。</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="plain-section">
      <h4>SLA 实例</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>业务</th>
            <th>状态</th>
            <th>响应截止</th>
            <th>处理截止</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="instance in instances" :key="instance.id">
            <td>{{ instance.business_type }} / {{ instance.business_id }}</td>
            <td>{{ instance.status }}</td>
            <td>{{ instance.response_due_at || '-' }}</td>
            <td>{{ instance.deadline_at || '-' }}</td>
          </tr>
          <tr v-if="instances.length === 0">
            <td colspan="4" class="empty-cell">暂无 SLA 实例。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
