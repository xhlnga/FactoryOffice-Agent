import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import AgentChatView from '../views/AgentChatView.vue'
import ApprovalsView from '../views/ApprovalsView.vue'
import AuditLogsView from '../views/AuditLogsView.vue'
import DashboardView from '../views/DashboardView.vue'
import KnowledgeBaseView from '../views/KnowledgeBaseView.vue'
import PurchasesView from '../views/PurchasesView.vue'
import TasksView from '../views/TasksView.vue'
import TicketsView from '../views/TicketsView.vue'
import WorkflowsView from '../views/WorkflowsView.vue'

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: DashboardView,
    meta: { title: '首页', showInMenu: true },
  },
  {
    path: '/knowledge',
    name: 'knowledge',
    component: KnowledgeBaseView,
    meta: { title: '知识库', showInMenu: true },
  },
  {
    path: '/agent',
    name: 'agent',
    component: AgentChatView,
    meta: { title: 'AI 助手', showInMenu: true },
  },
  {
    path: '/workflows',
    name: 'workflows',
    component: WorkflowsView,
    meta: { title: '办公流程', showInMenu: true },
  },
  {
    path: '/tasks',
    name: 'tasks',
    component: TasksView,
    meta: { title: '任务', showInMenu: true },
  },
  {
    path: '/tickets',
    name: 'tickets',
    component: TicketsView,
    meta: { title: '工单', showInMenu: true },
  },
  {
    path: '/purchases',
    name: 'purchases',
    component: PurchasesView,
    meta: { title: '采购', showInMenu: true },
  },
  {
    path: '/approvals',
    name: 'approvals',
    component: ApprovalsView,
    meta: { title: '审批', showInMenu: true },
  },
  {
    path: '/audit-logs',
    name: 'auditLogs',
    component: AuditLogsView,
    meta: { title: '审计日志', showInMenu: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
