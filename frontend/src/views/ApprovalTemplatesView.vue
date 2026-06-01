<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  createApprovalTemplate,
  listApprovalTemplates,
  type ApprovalTemplate,
  type ApprovalStepMode,
  type ApproverType,
} from '../api/approvalTemplates'

const templates = ref<ApprovalTemplate[]>([])
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

const form = ref({
  name: '采购申请审批',
  business_type: 'create_purchase_request',
  description: '按金额和角色进行采购审批。',
  min_amount: '',
  max_amount: '',
  step_name: '部门主管审批',
  approver_type: 'role' as ApproverType,
  approver_value: 'department_manager',
  mode: 'any' as ApprovalStepMode,
  timeout_hours: 24,
  escalate_to: 'general_manager',
})

async function loadTemplates() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listApprovalTemplates()
    templates.value = response.items
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '审批模板加载失败。'
  } finally {
    loading.value = false
  }
}

async function submitTemplate() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await createApprovalTemplate({
      name: form.value.name,
      business_type: form.value.business_type,
      description: form.value.description,
      min_amount: form.value.min_amount ? Number(form.value.min_amount) : null,
      max_amount: form.value.max_amount ? Number(form.value.max_amount) : null,
      steps: [
        {
          step_order: 1,
          name: form.value.step_name,
          approver_type: form.value.approver_type,
          approver_value: form.value.approver_value,
          mode: form.value.mode,
          timeout_hours: form.value.timeout_hours,
          escalate_to: form.value.escalate_to,
        },
      ],
    })
    message.value = response.message
    await loadTemplates()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '审批模板创建失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadTemplates)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>审批模板</h3>
        <p>维护采购、工单、质量异常等业务的多级审批模板。</p>
      </div>
      <button type="button" :disabled="loading" @click="loadTemplates">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>新增模板</h4>
      <div class="form-grid">
        <label>模板名称<input v-model="form.name" /></label>
        <label>业务类型<input v-model="form.business_type" /></label>
        <label>最小金额<input v-model="form.min_amount" type="number" /></label>
        <label>最大金额<input v-model="form.max_amount" type="number" /></label>
      </div>
      <div class="form-grid">
        <label>步骤名称<input v-model="form.step_name" /></label>
        <label>
          审批人类型
          <select v-model="form.approver_type">
            <option value="user">指定用户</option>
            <option value="role">指定角色</option>
            <option value="department_manager">部门主管</option>
            <option value="expression">表达式</option>
          </select>
        </label>
        <label>审批人/角色<input v-model="form.approver_value" /></label>
        <label>
          模式
          <select v-model="form.mode">
            <option value="any">或签</option>
            <option value="all">会签</option>
          </select>
        </label>
      </div>
      <div class="form-grid">
        <label>超时小时<input v-model.number="form.timeout_hours" type="number" /></label>
        <label>超时升级到<input v-model="form.escalate_to" /></label>
        <label class="wide-field">说明<input v-model="form.description" /></label>
      </div>
      <button type="button" :disabled="loading" @click="submitTemplate">保存模板</button>
    </section>

    <section class="plain-section">
      <h4>模板列表</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>名称</th>
            <th>业务类型</th>
            <th>金额范围</th>
            <th>状态</th>
            <th>步骤</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="template in templates" :key="template.id">
            <td>{{ template.name }}</td>
            <td>{{ template.business_type }}</td>
            <td>{{ template.min_amount ?? '-' }} - {{ template.max_amount ?? '-' }}</td>
            <td>{{ template.status }}</td>
            <td>
              <span v-for="step in template.steps" :key="step.id">
                {{ step.step_order }}.{{ step.name }}({{ step.mode }})&nbsp;
              </span>
            </td>
          </tr>
          <tr v-if="templates.length === 0">
            <td colspan="5" class="empty-cell">暂无审批模板。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
