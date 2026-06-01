<script setup lang="ts">
import { onMounted, ref } from 'vue'

import {
  createIntegration,
  disableIntegration,
  enableIntegration,
  listIntegrations,
  listNotificationDeliveries,
  testIntegration,
  type IntegrationConfig,
  type IntegrationPlatform,
  type NotificationDelivery,
} from '../api/integrations'

const configs = ref<IntegrationConfig[]>([])
const deliveries = ref<NotificationDelivery[]>([])
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

const form = ref({
  platform: 'local' as IntegrationPlatform,
  name: 'default',
  webhook_url: '',
  sign_secret: '',
})

async function loadData() {
  loading.value = true
  errorMessage.value = ''

  try {
    const [configResponse, deliveryResponse] = await Promise.all([
      listIntegrations(),
      listNotificationDeliveries(),
    ])
    configs.value = configResponse.items
    deliveries.value = deliveryResponse.items
    message.value = configResponse.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '企业集成配置加载失败。'
  } finally {
    loading.value = false
  }
}

async function submitConfig() {
  loading.value = true
  errorMessage.value = ''

  try {
    const encryptedConfig: Record<string, unknown> = {}
    if (form.value.sign_secret.trim()) {
      encryptedConfig.sign_secret = form.value.sign_secret.trim()
    }
    const response = await createIntegration({
      platform: form.value.platform,
      name: form.value.name,
      webhook_url: form.value.webhook_url.trim() || null,
      encrypted_config: encryptedConfig,
      enabled: form.value.platform === 'local',
    })
    message.value = response.message
    await loadData()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '企业集成配置创建失败。'
  } finally {
    loading.value = false
  }
}

async function toggleConfig(config: IntegrationConfig) {
  loading.value = true
  errorMessage.value = ''

  try {
    const response =
      config.status === 'active'
        ? await disableIntegration(config.id)
        : await enableIntegration(config.id)
    message.value = response.message
    await loadData()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '企业集成状态更新失败。'
  } finally {
    loading.value = false
  }
}

async function sendTest(configId: number) {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await testIntegration(configId)
    message.value = response.message
    if (!response.success && response.error_message) {
      errorMessage.value = response.error_message
    }
    await loadData()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '测试通知发送失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>企业集成</h3>
        <p>配置本地演示、通用 Webhook、企业微信、钉钉或飞书通知通道。</p>
      </div>
      <button type="button" :disabled="loading" @click="loadData">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>新增配置</h4>
      <div class="form-grid">
        <label>
          平台
          <select v-model="form.platform">
            <option value="local">本地演示</option>
            <option value="generic_webhook">通用 Webhook</option>
            <option value="wecom">企业微信机器人</option>
            <option value="dingtalk">钉钉机器人</option>
            <option value="feishu">飞书机器人</option>
          </select>
        </label>
        <label>配置名称<input v-model="form.name" /></label>
        <label>Webhook URL<input v-model="form.webhook_url" /></label>
        <label>签名密钥<input v-model="form.sign_secret" /></label>
      </div>
      <button type="button" :disabled="loading" @click="submitConfig">保存配置</button>
    </section>

    <section class="plain-section">
      <h4>配置列表</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>平台</th>
            <th>名称</th>
            <th>状态</th>
            <th>Webhook</th>
            <th>健康状态</th>
            <th>动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="config in configs" :key="config.id">
            <td>{{ config.platform }}</td>
            <td>{{ config.name }}</td>
            <td>{{ config.status }}</td>
            <td>{{ config.webhook_url || '-' }}</td>
            <td>{{ config.last_health_status || '-' }}</td>
            <td>
              <div class="table-actions">
                <button type="button" class="text-button" :disabled="loading" @click="toggleConfig(config)">
                  {{ config.status === 'active' ? '停用' : '启用' }}
                </button>
                <button type="button" class="text-button" :disabled="loading" @click="sendTest(config.id)">
                  测试
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="configs.length === 0">
            <td colspan="6" class="empty-cell">暂无集成配置。</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="plain-section">
      <h4>通知投递记录</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>平台</th>
            <th>标题</th>
            <th>业务</th>
            <th>状态</th>
            <th>响应码</th>
            <th>错误</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="delivery in deliveries" :key="delivery.id">
            <td>{{ delivery.platform }}</td>
            <td>{{ delivery.title || '-' }}</td>
            <td>{{ delivery.business_type || '-' }} / {{ delivery.business_id || '-' }}</td>
            <td>{{ delivery.status }}</td>
            <td>{{ delivery.response_code || '-' }}</td>
            <td>{{ delivery.last_error || '-' }}</td>
          </tr>
          <tr v-if="deliveries.length === 0">
            <td colspan="6" class="empty-cell">暂无通知投递记录。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
