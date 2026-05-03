<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'

import { routes } from './router'

const navigationItems = routes.filter((route) => route.meta?.showInMenu)
</script>

<template>
  <main class="app-shell">
    <aside class="side-menu" aria-label="主导航">
      <div class="brand">
        <span class="brand-mark">FO</span>
        <div>
          <h1>FactoryOffice-Agent</h1>
          <p>制造业企业知识库与办公流程智能体</p>
        </div>
      </div>

      <nav class="nav-list">
        <RouterLink
          v-for="item in navigationItems"
          :key="item.path"
          class="nav-item"
          :to="item.path"
        >
          {{ item.meta?.title }}
        </RouterLink>
      </nav>
    </aside>

    <section class="content-shell">
      <header class="top-bar">
        <div>
          <p class="eyebrow">企业级 Agent 工程样板</p>
          <h2>知识库、流程、审批、审计统一入口</h2>
        </div>
        <a class="api-link" href="/api/health" target="_blank" rel="noreferrer">后端健康检查</a>
      </header>

      <RouterView />
    </section>
  </main>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background: #f4f6f9;
  color: #182230;
  font-family:
    Inter,
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
}

.side-menu {
  min-height: 100vh;
  padding: 24px 18px;
  border-right: 1px solid #d6dee8;
  background: #ffffff;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 6px 4px 24px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #175cd3;
  color: #ffffff;
  font-weight: 700;
}

.brand h1 {
  margin: 0;
  font-size: 17px;
  line-height: 1.2;
}

.brand p {
  margin: 6px 0 0;
  color: #667085;
  font-size: 12px;
  line-height: 1.5;
}

.nav-list {
  display: grid;
  gap: 6px;
}

.nav-item {
  padding: 11px 12px;
  border-radius: 6px;
  color: #344054;
  text-decoration: none;
  font-size: 14px;
}

.nav-item:hover,
.nav-item.router-link-active {
  background: #eaf1ff;
  color: #175cd3;
}

.content-shell {
  min-width: 0;
  padding: 28px;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #667085;
  font-size: 13px;
}

.top-bar h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.api-link {
  flex: 0 0 auto;
  padding: 9px 12px;
  border: 1px solid #b2ccff;
  border-radius: 6px;
  color: #175cd3;
  background: #ffffff;
  text-decoration: none;
  font-size: 14px;
}

:deep(.view-stack) {
  display: grid;
  gap: 18px;
}

:deep(.plain-section),
:deep(.metric-card),
:deep(.chat-message) {
  padding: 28px;
  border: 1px solid #d6dee8;
  border-radius: 8px;
  background: #ffffff;
}

:deep(.plain-section) {
  overflow-x: auto;
}

:deep(.section-header) {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

:deep(.section-header h3) {
  margin: 0;
  color: #101828;
  font-size: 24px;
}

:deep(.section-header p),
:deep(.muted-text) {
  max-width: 760px;
  margin: 8px 0 0;
  color: #344054;
  line-height: 1.7;
}

:deep(.plain-section h4) {
  margin: 0 0 16px;
  color: #101828;
  font-size: 17px;
}

:deep(.form-row),
:deep(.action-row),
:deep(.tab-row),
:deep(.table-actions) {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
}

:deep(.form-grid) {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

:deep(label) {
  display: grid;
  color: #475467;
  font-size: 14px;
  gap: 6px;
}

:deep(input),
:deep(select),
:deep(textarea) {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 10px 11px;
  color: #182230;
  background: #ffffff;
  font: inherit;
}

:deep(textarea) {
  resize: vertical;
  line-height: 1.7;
}

:deep(button) {
  border: 1px solid #175cd3;
  border-radius: 6px;
  padding: 10px 14px;
  color: #ffffff;
  background: #175cd3;
  cursor: pointer;
  font: inherit;
}

:deep(button:disabled) {
  border-color: #cfd7e3;
  background: #98a2b3;
  cursor: not-allowed;
}

:deep(.secondary-button),
:deep(.tab-row button) {
  color: #175cd3;
  background: #ffffff;
}

:deep(.tab-row button.active) {
  color: #ffffff;
  background: #175cd3;
}

:deep(.text-button) {
  border: 0;
  padding: 0;
  color: #175cd3;
  background: transparent;
}

:deep(.text-button.danger) {
  color: #b42318;
}

:deep(.data-table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

:deep(.data-table th),
:deep(.data-table td) {
  border-bottom: 1px solid #e4e7ec;
  padding: 12px 10px;
  text-align: left;
  vertical-align: top;
}

:deep(.data-table th) {
  color: #475467;
  background: #f8fafc;
  font-weight: 600;
}

:deep(.empty-cell) {
  color: #667085;
  text-align: center;
}

:deep(.success-text) {
  color: #067647;
}

:deep(.error-text) {
  color: #b42318;
}

:deep(.result-box),
:deep(.json-box) {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #d6dee8;
  border-radius: 6px;
  background: #f8fafc;
  color: #344054;
  overflow-x: auto;
}

:deep(.result-box.compact) {
  padding: 10px 12px;
}

:deep(.metric-grid) {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 14px;
}

:deep(.metric-card) {
  display: grid;
  gap: 8px;
}

:deep(.metric-card span) {
  color: #667085;
  font-size: 14px;
}

:deep(.metric-card strong) {
  color: #101828;
  font-size: 28px;
}

:deep(.chat-list) {
  display: grid;
  gap: 12px;
  margin-bottom: 14px;
}

:deep(.chat-message) {
  padding: 16px;
}

:deep(.chat-message[data-role='user']) {
  background: #f8fafc;
}

:deep(.mono-cell),
:deep(.json-box),
:deep(.json-pre) {
  font-family:
    "SFMono-Regular",
    Consolas,
    "Liberation Mono",
    monospace;
  font-size: 13px;
}

:deep(.json-pre) {
  max-width: 460px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 860px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .side-menu {
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid #d6dee8;
  }

  .nav-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-shell {
    padding: 20px;
  }

  .top-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  :deep(.section-header) {
    flex-direction: column;
  }

  :deep(.form-grid),
  :deep(.metric-grid) {
    grid-template-columns: 1fr;
  }
}
</style>
