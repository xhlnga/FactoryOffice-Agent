# 数据库设计

本文档说明 FactoryOffice-Agent 的核心数据实体。项目事实和功能边界以 [`../00_project_truth/PROJECT_SSOT.md`](../00_project_truth/PROJECT_SSOT.md) 为准。

## 1. 设计目标

数据库同时承载两类数据：

- 知识库数据：文档、文档切块、向量、元数据。
- 办公流程数据：用户、任务、工单、采购申请、审批、审计日志。

选择 PostgreSQL + pgvector 的原因：

- 业务数据和向量数据可以放在同一个数据库中。
- 便于文档、流程、审批和日志之间建立关联。
- 适合本地部署和开源演示。
- 后续可以扩展精确检索、向量检索和混合检索。

## 2. 核心表

### users

用户表，用于本地身份模拟和后续权限扩展。

| 字段 | 说明 |
| --- | --- |
| `id` | 用户 ID |
| `username` | 用户名 |
| `role` | 用户角色 |
| `department` | 所属部门 |
| `created_at` | 创建时间 |

角色枚举：

```text
admin
manager
employee
```

### documents

文档表，保存上传文档的基本信息。

| 字段 | 说明 |
| --- | --- |
| `id` | 文档 ID |
| `filename` | 文件名 |
| `title` | 文档标题 |
| `category` | 文档分类 |
| `file_path` | 本地文件路径 |
| `file_hash` | 文件哈希，用于去重 |
| `file_size` | 文件大小 |
| `uploaded_by` | 上传人 |
| `is_deleted` | 是否软删除 |
| `created_at` | 创建时间 |

说明：

- 制度、SOP、设备手册、质量流程等文档不建议硬删除。
- 删除动作应进入审批，通过后执行软删除。

### document_chunks

文档切块表，用于 RAG 检索。

| 字段 | 说明 |
| --- | --- |
| `id` | 切块 ID |
| `document_id` | 所属文档 |
| `chunk_text` | 切块文本 |
| `chunk_index` | 切块序号 |
| `embedding` | 向量 |
| `metadata` | 额外元数据 |
| `created_at` | 创建时间 |

说明：

- 每个文档解析后会拆成多个 chunk。
- 用户提问时先检索相关 chunk，再构造回答。

### tasks

任务表，用于保存会议纪要转任务后的结果。

| 字段 | 说明 |
| --- | --- |
| `id` | 任务 ID |
| `title` | 任务标题 |
| `description` | 任务描述 |
| `assignee` | 负责人 |
| `due_date` | 截止日期 |
| `priority` | 优先级 |
| `status` | 任务状态 |
| `source` | 任务来源 |
| `created_at` | 创建时间 |

优先级：

```text
low
medium
high
urgent
```

任务状态：

```text
todo
in_progress
done
cancelled
```

### tickets

工单表，用于设备维修、质量异常、安全隐患等流程。

| 字段 | 说明 |
| --- | --- |
| `id` | 工单 ID |
| `ticket_type` | 工单类型 |
| `title` | 工单标题 |
| `description` | 工单描述 |
| `priority` | 优先级 |
| `status` | 工单状态 |
| `created_by` | 创建人 |
| `created_at` | 创建时间 |

工单状态：

```text
open
processing
resolved
closed
```

### purchase_requests

采购申请表，用于保存人工确认后的采购申请。

| 字段 | 说明 |
| --- | --- |
| `id` | 采购申请 ID |
| `item_name` | 物品名称 |
| `quantity` | 数量 |
| `reason` | 采购原因 |
| `budget` | 预算金额 |
| `supplier` | 供应商 |
| `status` | 采购状态 |
| `created_by` | 创建人 |
| `created_at` | 创建时间 |

采购状态：

```text
draft
pending_approval
approved
rejected
```

### approvals

审批表，保存 Agent 建议执行但需要人工确认的动作。

| 字段 | 说明 |
| --- | --- |
| `id` | 审批 ID |
| `action_type` | 动作类型 |
| `action_payload` | 动作参数 |
| `status` | 审批状态 |
| `reviewer` | 审批人 |
| `reviewed_at` | 审批时间 |
| `executed_at` | 执行时间 |
| `execution_result` | 执行结果 |
| `comment` | 审批意见 |
| `created_at` | 创建时间 |

审批状态：

```text
pending
approved
rejected
execution_failed
```

常见动作类型：

```text
create_purchase_request
create_maintenance_ticket
create_tasks
delete_document
```

### audit_logs

审计日志表，记录用户输入、模型输出、工具调用和执行结果。

| 字段 | 说明 |
| --- | --- |
| `id` | 日志 ID |
| `user_id` | 用户 ID |
| `action` | 动作名称 |
| `input` | 用户输入 |
| `output` | 模型或工具输出 |
| `tool_name` | 工具名称 |
| `tool_args` | 工具参数 |
| `status` | 执行状态 |
| `created_at` | 创建时间 |

执行状态：

```text
success
failed
pending
```

## 3. 数据关系

```text
users
  ├── documents.uploaded_by
  ├── tickets.created_by
  ├── purchase_requests.created_by
  └── audit_logs.user_id

documents
  └── document_chunks.document_id

approvals
  └── action_payload 指向待执行动作参数

audit_logs
  └── 记录知识库问答、工作流、审批和工具执行过程
```

## 4. 初始化数据

演示数据位于 `data/seed/`：

```text
users.json
tasks.json
tickets.json
purchase_requests.json
approvals.json
audit_logs.json
```

这些数据用于让前端页面和演示流程启动后有可查看内容。

## 5. 数据安全约束

- 用户上传文件不提交到代码仓库。
- 制度、SOP、手册类文档删除应走审批。
- 高风险动作必须有 approvals 记录。
- 工具执行结果必须进入 audit_logs。
- 演示数据不得使用真实企业内部资料。
