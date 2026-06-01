# 企业集成层设计

FactoryOffice-Agent 的企业集成层目标不是替代所有 OA/ERP/MES，而是提供统一接口，让 Agent 可以安全进入企业流程。

## 核心原则

- 业务代码不直接调用企业微信、钉钉、飞书、OA、ERP、MES。
- 所有外部调用走 Provider。
- 所有回调走幂等检查。
- 外部同步失败只记录和重试，不回滚已经审批通过的本地业务。
- 没有企业上下文时，不允许误用真实外部系统配置。

## 模块结构

```text
backend/app/integrations/
├── core/          # Provider 抽象、Schema、注册中心、幂等
├── providers/     # local、企业微信、钉钉、飞书、通用 OA/ERP/MES/WMS
├── services/      # 通知、组织同步、SSO、审批桥接、业务同步、SLA
└── callbacks/     # 平台回调解析
```

后台任务：

```text
backend/app/jobs/
├── worker.py
├── notification_jobs.py
├── org_sync_jobs.py
├── sla_jobs.py
├── business_sync_jobs.py
└── cleanup_jobs.py
```

## 典型闭环

```text
用户提交采购申请
  ↓
Agent 补字段并生成草稿
  ↓
审批引擎选择模板
  ↓
通知服务发送待办
  ↓
用户通过签名 H5 链接审批
  ↓
本地业务表写入
  ↓
业务同步服务写入 ERP
  ↓
失败进入后台重试
  ↓
审计日志保留过程
```

## 外部系统同步

外部同步统一记录到 `external_id_mappings`：

```text
external_system
external_id
sync_status
last_error
retry_count
last_sync_at
```

失败记录由 `business_sync_jobs.py` 扫描并重试。

## 组织与权限

组织同步先由 Provider 读取人员和部门快照，再逐步落到企业、部门、用户、角色表。RAG 检索通过文档权限过滤，避免普通员工检索到无权查看的制度、采购、质量或安全资料。

## 生产边界

本项目提供企业接入框架和通用 Webhook 适配器。真实落地时，仍需根据企业具体 OA/ERP/MES/WMS 字段、权限和审批模板做映射配置。
