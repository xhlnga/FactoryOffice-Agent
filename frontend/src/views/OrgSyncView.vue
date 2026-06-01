<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  listIntegrations,
  previewOrgSync,
  runOrgSync,
  type IntegrationConfig,
} from '../api/integrations'

const configs = ref<IntegrationConfig[]>([])
const selectedConfigId = ref<number | ''>('')
const preview = ref<Record<string, unknown> | null>(null)
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

async function loadConfigs() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listIntegrations()
    configs.value = response.items
    selectedConfigId.value = response.items[0]?.id || ''
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '集成配置加载失败。'
  } finally {
    loading.value = false
  }
}

async function previewSync() {
  if (!selectedConfigId.value) {
    errorMessage.value = '请先选择集成配置。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await previewOrgSync(Number(selectedConfigId.value))
    preview.value = response.preview
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '组织同步预览失败。'
  } finally {
    loading.value = false
  }
}

async function syncNow() {
  if (!selectedConfigId.value) {
    errorMessage.value = '请先选择集成配置。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await runOrgSync(Number(selectedConfigId.value))
    preview.value = response.result
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '组织同步失败。'
  } finally {
    loading.value = false
  }
}

function pretty(value: unknown) {
  return JSON.stringify(value, null, 2)
}

onMounted(loadConfigs)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>组织同步</h3>
        <p>读取企业平台中的部门和人员快照，为后续权限、审批人和通知对象映射提供基础。</p>
      </div>
      <button type="button" :disabled="loading" @click="loadConfigs">刷新配置</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>同步操作</h4>
      <div class="form-row">
        <label>
          集成配置
          <select v-model="selectedConfigId">
            <option value="">请选择</option>
            <option v-for="config in configs" :key="config.id" :value="config.id">
              {{ config.platform }} / {{ config.name }} / {{ config.status }}
            </option>
          </select>
        </label>
        <button type="button" :disabled="loading" @click="previewSync">预览</button>
        <button type="button" :disabled="loading" @click="syncNow">同步</button>
      </div>
    </section>

    <section class="plain-section">
      <h4>同步结果</h4>
      <pre class="json-pre">{{ preview ? pretty(preview) : '暂无同步结果。' }}</pre>
    </section>
  </section>
</template>
