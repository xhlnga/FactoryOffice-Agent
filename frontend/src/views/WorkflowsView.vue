<script setup lang="ts">
import { computed, ref } from 'vue'

import {
  generateMaintenanceTicket,
  generateMeetingTasks,
  generatePurchaseRequest,
  generateQualityIssue,
  generateWeeklyReport,
} from '../api/workflows'

type WorkflowKey = 'meeting' | 'maintenance' | 'quality' | 'purchase' | 'weekly'

const workflowOptions: Array<{ key: WorkflowKey; label: string; sample: string }> = [
  {
    key: 'meeting',
    label: '会议纪要转任务',
    sample: '今天会议确定：张工周五前完成设备巡检方案；李工下周一前联系供应商确认交期；王经理负责审批采购预算。',
  },
  {
    key: 'maintenance',
    label: '设备异常转工单',
    sample: '空压机 E07 报警，压力传感器读数异常，生产线 A 暂停。',
  },
  {
    key: 'quality',
    label: '质量异常处理',
    sample: 'B2批次零件抽检发现3件尺寸超差，影响当前批次出货，请生成质量异常单草稿。',
  },
  {
    key: 'purchase',
    label: '采购申请草稿',
    sample: '申请采购 20 个温度传感器，预算 48000 元，供应商为华东传感器有限公司，用于产线设备改造。',
  },
  {
    key: 'weekly',
    label: '项目周报生成',
    sample: '本周完成设备巡检方案，质量异常关闭 2 项，温度传感器采购待确认交期，下周计划完成产线改造评审。',
  },
]

const activeWorkflow = ref<WorkflowKey>('meeting')
const content = ref(workflowOptions[0].sample)
const loading = ref(false)
const errorMessage = ref('')
const result = ref<unknown>(null)

const activeOption = computed(() => workflowOptions.find((item) => item.key === activeWorkflow.value))

function selectWorkflow(key: WorkflowKey) {
  activeWorkflow.value = key
  content.value = workflowOptions.find((item) => item.key === key)?.sample || ''
  result.value = null
  errorMessage.value = ''
}

async function runWorkflow() {
  if (!content.value.trim()) {
    errorMessage.value = '请输入流程所需的业务内容。'
    return
  }

  loading.value = true
  errorMessage.value = ''
  result.value = null

  try {
    if (activeWorkflow.value === 'meeting') {
      result.value = await generateMeetingTasks(content.value)
    } else if (activeWorkflow.value === 'maintenance') {
      result.value = await generateMaintenanceTicket(content.value)
    } else if (activeWorkflow.value === 'quality') {
      result.value = await generateQualityIssue(content.value)
    } else if (activeWorkflow.value === 'purchase') {
      result.value = await generatePurchaseRequest(content.value)
    } else {
      result.value = await generateWeeklyReport(content.value)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '办公流程执行失败。'
  } finally {
    loading.value = false
  }
}

function formatResult(value: unknown) {
  return JSON.stringify(value, null, 2)
}
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>办公流程</h3>
        <p>固定流程先生成草稿，正式写入由人工确认和审批控制。</p>
      </div>
    </div>

    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>选择流程</h4>
      <div class="tab-row">
        <button
          v-for="option in workflowOptions"
          :key="option.key"
          type="button"
          :class="{ active: activeWorkflow === option.key }"
          @click="selectWorkflow(option.key)"
        >
          {{ option.label }}
        </button>
      </div>

      <label>
        {{ activeOption?.label || '流程内容' }}
        <textarea v-model="content" rows="8" />
      </label>

      <div class="action-row">
        <button type="button" :disabled="loading" @click="runWorkflow">
          {{ loading ? '生成中...' : '生成草稿' }}
        </button>
      </div>

      <pre v-if="result" class="json-box">{{ formatResult(result) }}</pre>
    </section>
  </section>
</template>
