<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { createPurchase, listPurchases, type PurchaseItem } from '../api/purchases'

const purchases = ref<PurchaseItem[]>([])
const total = ref(0)
const loading = ref(false)
const message = ref('')
const errorMessage = ref('')

const form = reactive({
  item_name: '',
  quantity: 1 as number | string,
  reason: '',
  budget: undefined as number | string | undefined,
  supplier: '',
})

async function loadPurchases() {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listPurchases()
    purchases.value = response.items
    total.value = response.total
    message.value = response.message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '采购申请列表加载失败。'
  } finally {
    loading.value = false
  }
}

async function submitPurchase() {
  if (!form.item_name.trim()) {
    errorMessage.value = '物品名称不能为空。'
    return
  }

  const quantity = Number(form.quantity)
  const budget = form.budget == null || form.budget === '' ? null : Number(form.budget)

  if (!Number.isInteger(quantity) || quantity < 1) {
    errorMessage.value = '采购数量必须是大于 0 的整数。'
    return
  }

  if (budget !== null && (!Number.isFinite(budget) || budget < 0)) {
    errorMessage.value = '预算金额不能小于 0。'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await createPurchase({
      item_name: form.item_name,
      quantity,
      reason: form.reason,
      budget,
      supplier: form.supplier || null,
    })
    message.value = `${response.message} 审批单号：${response.approval.id}`
    await loadPurchases()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '采购申请创建失败。'
  } finally {
    loading.value = false
  }
}

onMounted(loadPurchases)
</script>

<template>
  <section class="view-stack">
    <div class="section-header">
      <div>
        <h3>采购申请</h3>
        <p>采购申请默认属于需确认动作，预算、供应商和用途应尽量补齐。</p>
      </div>
      <button type="button" @click="loadPurchases">刷新</button>
    </div>

    <p v-if="message" class="muted-text">{{ message }}</p>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

    <section class="plain-section">
      <h4>创建采购申请</h4>
      <div class="form-grid">
        <label>物品名称<input v-model="form.item_name" /></label>
        <label>数量<input v-model.number="form.quantity" type="number" min="1" /></label>
        <label>预算金额<input v-model.number="form.budget" type="number" min="0" /></label>
        <label>供应商<input v-model="form.supplier" /></label>
      </div>
      <label>采购原因<textarea v-model="form.reason" rows="4" /></label>
      <div class="action-row">
        <button type="button" :disabled="loading" @click="submitPurchase">提交</button>
      </div>
    </section>

    <section class="plain-section">
      <h4>采购申请列表（{{ total }}）</h4>
      <table class="data-table">
        <thead>
          <tr>
            <th>物品</th>
            <th>数量</th>
            <th>预算</th>
            <th>供应商</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="purchase in purchases" :key="purchase.id">
            <td>{{ purchase.item_name }}</td>
            <td>{{ purchase.quantity }}</td>
            <td>{{ purchase.budget ?? '-' }}</td>
            <td>{{ purchase.supplier || '-' }}</td>
            <td>{{ purchase.status }}</td>
          </tr>
          <tr v-if="purchases.length === 0">
            <td colspan="5" class="empty-cell">暂无采购申请。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
