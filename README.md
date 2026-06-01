# FactoryOffice-Agent

制造业企业知识库与办公流程智能体。

FactoryOffice-Agent 是一个面向制造业企业办公场景的 AI Agent 工程样板。项目围绕企业制度、SOP、设备手册、质量流程、安全规范和项目资料，提供知识库问答、流程草稿生成、人工审批、工具执行和审计追踪能力。

它是一个把企业办公中的“查资料、写草稿、走审批、落业务表、留日志”串起来的完整工程闭环。

完整项目事实、范围和边界见：[`00_project_truth/PROJECT_SSOT.md`](00_project_truth/PROJECT_SSOT.md)

面向业务和管理人员的说明见：[`SUPERVISOR_COMPATIBILITY.md`](SUPERVISOR_COMPATIBILITY.md)

## 项目价值

制造业企业的日常办公通常是围绕制度、流程、设备、质量、采购、项目交付展开。

企业员工常见问题包括：

```text
采购超过 5 万需要谁审批？
空压机 E07 报警应先排查什么？
这批零件尺寸超差，质量异常流程怎么走？
会议纪要里哪些事项需要生成任务？
采购滤芯需要补哪些字段？
本周设备风险、质量风险和采购风险怎么写进周报？
```

这些问题的特点是：

- 需要查企业内部资料。
- 需要引用来源。
- 需要转成任务、工单、采购申请或周报草稿。
- 涉及预算、安全、质量、客户交付时不能让 AI 自动决定。
- 执行后需要留下审批和审计记录。

FactoryOffice-Agent 正是围绕这些真实约束设计。

## 核心流程

```text
员工提问 / 上传文件 / 输入业务描述
        ↓
Agent 判断任务类型
        ↓
检索企业知识库或进入固定工作流
        ↓
生成回答、任务草稿、工单草稿、采购申请草稿或周报草稿
        ↓
正式业务写入进入人工审批
        ↓
审批通过后调用工具写入业务表
        ↓
记录审计日志，便于追踪和复盘
```

这个流程体现了企业 AI 应用的基本原则：AI 辅助准备材料，人负责确认和决策，系统负责记录和追踪。

## Agent 编排机制

FactoryOffice-Agent 采用“任务状态机 + SOP 配置 + 多轮补槽 + 审批门控 + Trace”的流程型 Agent 编排方式。

Agent 不追求自由行动，而是围绕企业可控流程推进：

```text
识别意图
  ↓
匹配 SOP
  ↓
检查必填字段
  ↓
缺字段时进入 collecting_info 并追问
  ↓
字段完整后生成草稿
  ↓
需要正式写入时进入 waiting_approval
  ↓
审批通过后执行工具并写入审计日志
```

当前任务状态包括：

```text
new
collecting_info
waiting_approval
approved
executing
completed
failed
cancelled
suspended
```

Agent 响应会返回结构化 Trace，例如：

```text
识别意图：purchase_request
命中 SOP：采购申请 SOP
缺失字段：预算、供应商
下一步状态：collecting_info
是否需要审批：否
```

这使系统更适合企业场景：流程可解释、状态可追踪、动作可审批、结果可审计。

## 企业集成与移动审批

项目已经预留企业集成层，用统一 Provider 抽象连接本地演示、通用 Webhook、企业微信、钉钉和飞书通知通道。

当前最小闭环是：

```text
审批创建
  ↓
按已启用集成配置发送待办通知
  ↓
通知中携带带签名 token 的 H5 审批链接
  ↓
审批人打开移动审批页批准或拒绝
  ↓
审批引擎更新状态并继续流转
  ↓
系统写入通知投递记录、回调事件和审计日志
```

当前实现重点是“通知 + 签名 H5 审批 + 回调入口 + 投递记录”，不是把企业微信、钉钉、飞书的完整 OAuth、通讯录同步和原生审批 API 一次性写死到业务代码里。这样后续可以按企业实际平台逐步替换 Provider，而不影响审批、工单、采购和审计主流程。

## 当前功能

### 企业知识库问答

支持上传、解析和检索企业文档。

当前支持：

- Markdown
- TXT
- PDF
- DOCX

上传后系统会完成：

- 文件大小限制检查
- 文件哈希去重
- 文档解析
- 文本切块
- 向量化
- pgvector 入库

问答时系统会返回答案和引用来源，降低无来源回答风险。

### 会议纪要转任务

系统可以从会议纪要中提取任务草稿：

- 任务标题
- 任务描述
- 负责人
- 截止时间
- 优先级
- 来源标识

批量创建任务前会进入人工确认。会议原文保留在审批参数中，正式任务表只写受控来源标签，避免污染业务字段。

### 设备异常转维修工单

员工输入设备异常描述后，系统生成维修工单草稿。

示例：

```text
A3 产线空压机 E07 报警，末端压力波动，产线暂停 35 分钟。
```

系统会整理：

- 工单类型
- 工单标题
- 优先级
- 异常描述
- 初步排查建议
- 是否需要人工确认

提交正式工单前必须审批。

### 质量异常处理

系统可以根据质量异常描述生成 NCR 或质量异常工单草稿。

示例：

```text
B2 批次零件抽检发现 3 件尺寸超差，影响当前批次出货。
```

系统会整理：

- 异常类型
- 影响范围
- 初步处置建议
- 后续确认动作
- 是否需要质量负责人确认

系统不会直接判定最终责任，不会直接决定放行、返工或报废。

### 采购申请草稿

系统可以从自然语言中提取采购申请字段：

- 物品名称
- 数量
- 采购原因
- 预算金额
- 供应商

如果字段不完整，系统会提示补充。字段完整后，生成采购申请草稿并进入审批。

### 项目周报草稿

系统可以从项目记录中生成周报草稿：

- 本周进展
- 本周问题
- 质量风险
- 设备风险
- 采购风险
- 下周计划
- 需要管理层决策事项

周报草稿需要项目负责人复核后使用。

### 人工审批

高风险或正式业务动作不会直接执行。

需要进入审批的动作包括：

- 创建任务
- 批量创建任务
- 提交维修工单
- 提交质量异常工单
- 提交采购申请
- 删除知识库文档

审批通过后，系统才会调用对应服务写入业务表。

### 审计日志

系统记录关键过程：

- 用户输入
- 动作类型
- 工具名称
- 工具参数
- 审批状态
- 执行结果
- 执行时间

审计日志用于追踪、复盘和排查问题。

## 为什么说很接近真实

不只是文档内容，而是业务机制和工程结构。

### 1. 有企业知识库

系统不是直接让模型凭记忆回答，而是先检索企业文档，再生成回答和引用来源。

### 2. 有业务对象

系统不是只有聊天记录，而是有明确业务表：

```text
users
documents
document_chunks
tasks
tickets
purchase_requests
approvals
audit_logs
```

这些对象对应企业真实办公系统中的用户、文档、任务、工单、采购申请、审批和日志。

### 3. 有审批控制

AI 生成的是草稿和建议。正式业务写入需要人工确认。

这符合企业对安全、质量、预算、客户交付和责任边界的要求。

### 4. 有审计追踪

工具调用参数和执行结果会写入审计日志。系统不是黑箱。

### 5. 有企业集成和外部系统边界

当前版本默认用本地数据库跑通任务、工单、采购、审批和日志闭环，同时提供企业集成配置、通用 Webhook、企业微信/钉钉/飞书通知、签名 H5 审批链接、组织同步、SLA 和 OA/ERP/MES/WMS 同步适配边界。接真实企业系统时，主要是补企业开放平台配置、回调验签、字段映射和联调。

## 演示数据

项目内置制造业模拟文档，位于 `data/demo_docs/`：

```text
采购管理制度.md
差旅报销制度.md
设备维修手册_空压机.md
质量异常处理流程.md
安全生产规范.md
项目周报模板.md
```

项目内置初始化业务数据，位于 `data/seed/`：

```text
users.json
tasks.json
tickets.json
purchase_requests.json
approvals.json
audit_logs.json
```

这些数据均为模拟内容，用于本地演示、流程验证和功能开发，不包含真实企业内部资料。

## 技术栈

| 模块 | 技术选择 |
| --- | --- |
| 后端 | Python + FastAPI |
| 前端 | Vue3 + Element Plus |
| Agent 编排 | LangGraph + 本地降级执行器 |
| 大模型接口 | OpenAI-compatible API |
| 向量检索 | PostgreSQL + pgvector |
| ORM | SQLAlchemy |
| 数据库迁移 | Alembic |
| 文件存储 | 本地 uploads 目录 |
| 文档解析 | PyMuPDF / python-docx / Markdown / TXT |
| 部署 | Docker Compose |
| 测试 | unittest |

## 系统结构


<img width="1400" height="920" alt="image" src="https://github.com/user-attachments/assets/089fe4ee-7a91-42ba-b5b2-d9352ed3dadf" />




```text
FactoryOffice-Agent/
├── 00_project_truth/                         # 项目事实中心
│   └── PROJECT_SSOT.md                       # 项目唯一真源，定义定位、范围、边界、技术栈、工作流和不做什么

├── backend/                                  # FastAPI 后端服务
│   ├── app/                                  # 后端主应用代码
│   │   ├── __init__.py                       # Python 包标识
│   │   ├── main.py                           # FastAPI 入口，创建 app、挂载路由、配置 CORS、自定义 Swagger 样式

│   │   ├── api/                              # HTTP API 路由层
│   │   │   ├── __init__.py                   # API 包标识
│   │   │   └── v1/                           # API v1 版本目录
│   │   │       ├── __init__.py               # v1 包标识
│   │   │       ├── router.py                 # API 总路由，统一注册所有 endpoints
│   │   │       └── endpoints/                # 具体业务接口
│   │   │           ├── __init__.py           # endpoints 包标识
│   │   │           ├── health.py             # 健康检查接口
│   │   │           ├── auth.py               # 本地登录、当前用户和身份模拟接口
│   │   │           ├── documents.py          # 文档上传、列表、详情、删除申请接口
│   │   │           ├── knowledge.py          # 知识库检索和问答接口
│   │   │           ├── agent.py              # Agent 对话入口，返回意图、SOP、补槽、Trace、工具预览
│   │   │           ├── workflows.py          # 会议、维修、质量、采购、周报工作流接口
│   │   │           ├── tasks.py              # 任务列表、详情、创建任务申请接口
│   │   │           ├── tickets.py            # 工单列表、详情、创建维修/质量工单申请接口
│   │   │           ├── purchases.py          # 采购申请列表、详情、创建采购申请接口
│   │   │           ├── approvals.py          # 简单审批列表、批准、拒绝接口
│   │   │           ├── approval_templates.py # 审批模板、审批步骤、多级审批配置接口
│   │   │           ├── audit_logs.py         # 审计日志列表和详情接口
│   │   │           ├── integrations.py       # 企业微信/钉钉/飞书/Webhook 集成配置和测试接口
│   │   │           ├── callbacks.py          # 外部平台回调入口，处理审批/通知/事件回调
│   │   │           ├── mobile_approvals.py   # H5 移动审批详情、批准、拒绝接口
│   │   │           └── sla.py                # SLA 策略和 SLA 实例查询配置接口

│   │   ├── core/                             # 后端基础设施层
│   │   │   ├── __init__.py                   # core 包标识
│   │   │   ├── config.py                     # 环境变量、数据库、上传目录、模型、CORS、Redis、集成配置
│   │   │   ├── database.py                   # SQLAlchemy Engine、Session、本地数据库依赖
│   │   │   ├── auth.py                       # 登录态/JWT/当前用户解析的基础能力
│   │   │   ├── permissions.py                # RBAC 和数据范围权限判断
│   │   │   ├── security.py                   # 兼容旧版角色权限控制
│   │   │   ├── logging.py                    # 日志格式、日志级别、日志初始化
│   │   │   └── exceptions.py                 # 统一业务异常和 FastAPI 异常处理

│   │   ├── models/                           # SQLAlchemy 数据库模型
│   │   │   ├── __init__.py                   # 模型统一导入，保证 Alembic 可发现表
│   │   │   ├── base.py                       # Base、通用时间字段、枚举和基础模型
│   │   │   ├── user.py                       # 用户表，兼容旧角色字段并支持企业、部门、外部用户 ID
│   │   │   ├── enterprise.py                 # 企业/租户表，一家公司一个 enterprise
│   │   │   ├── department.py                 # 部门表，支持外部部门 ID、父子部门和部门路径
│   │   │   ├── role.py                       # 企业角色表，如采购、质量、设备、财务、管理员
│   │   │   ├── user_role.py                  # 用户和角色多对多关系表
│   │   │   ├── document.py                   # 文档表，记录文件、分类、哈希、软删除和权限信息
│   │   │   ├── document_chunk.py             # 文档切块表，保存 chunk、元数据和 pgvector 向量
│   │   │   ├── document_permission.py        # 文档权限表，控制部门/角色/用户可见范围
│   │   │   ├── task.py                       # 任务表，保存会议纪要转任务后的正式任务
│   │   │   ├── ticket.py                     # 工单表，覆盖设备维修和质量异常工单
│   │   │   ├── purchase_request.py           # 采购申请表，保存物品、数量、预算、供应商、状态
│   │   │   ├── approval.py                   # 兼容版审批表，记录待确认动作和审批结果
│   │   │   ├── approval_template.py          # 审批模板表，定义不同业务类型的审批规则
│   │   │   ├── approval_step.py              # 审批步骤表，定义步骤顺序、审批人类型、会签/或签
│   │   │   ├── approval_instance.py          # 审批实例表，一次真实审批流程的主记录
│   │   │   ├── approval_instance_step.py     # 审批实例步骤表，记录每一步审批状态
│   │   │   ├── approval_action.py            # 审批动作表，记录批准、拒绝、转交、撤回、评论
│   │   │   ├── audit_log.py                  # 审计日志表，记录输入、工具参数、执行结果和状态
│   │   │   ├── integration_config.py         # 企业集成配置表，保存平台、密钥引用、Webhook、启用状态
│   │   │   ├── integration_event.py          # 外部回调事件表，记录事件、处理状态、失败原因、重试次数
│   │   │   ├── notification_delivery.py      # 通知发送记录表，记录平台、接收人、发送结果和重试信息
│   │   │   ├── external_id_mapping.py        # 本地对象和外部系统对象 ID 映射表
│   │   │   ├── idempotency_key.py            # 幂等键表，防止重复回调、重复审批、重复同步
│   │   │   └── sla.py                        # SLA 策略和 SLA 实例表

│   │   ├── schemas/                          # Pydantic 请求和响应结构
│   │   │   ├── __init__.py                   # schemas 包标识
│   │   │   ├── common.py                     # 通用响应、分页和基础结构
│   │   │   ├── user.py                       # 用户、登录、当前用户响应结构
│   │   │   ├── document.py                   # 文档上传、读取、切块、删除申请结构
│   │   │   ├── knowledge.py                  # 知识库搜索、问答、引用来源结构
│   │   │   ├── agent.py                      # Agent 请求、响应、SOP、补槽、Trace、工具调用结构
│   │   │   ├── workflow.py                   # 会议、维修、质量、采购、周报工作流结构
│   │   │   ├── task.py                       # 任务创建、读取和更新结构
│   │   │   ├── ticket.py                     # 工单创建、读取和更新结构
│   │   │   ├── purchase_request.py           # 采购申请创建、读取和更新结构
│   │   │   ├── approval.py                   # 简单审批创建、读取、批准、拒绝结构
│   │   │   ├── approval_template.py          # 审批模板、步骤、审批实例响应结构
│   │   │   ├── audit_log.py                  # 审计日志读取结构
│   │   │   ├── integration.py                # 企业集成配置、测试连接、通知响应结构
│   │   │   ├── mobile_approval.py            # 移动审批详情、批准、拒绝结构
│   │   │   └── sla.py                        # SLA 策略、实例、提醒升级结构

│   │   ├── services/                         # 业务服务层
│   │   │   ├── __init__.py                   # services 包标识
│   │   │   ├── document_service.py           # 文档保存、大小限制、哈希去重、解析、切块、软删除申请
│   │   │   ├── knowledge_service.py          # 串联 RAG 检索、Prompt、LLM 回答和引用来源
│   │   │   ├── task_service.py               # 任务创建、查询、审批保护和外部 OA 同步触发
│   │   │   ├── ticket_service.py             # 工单创建、查询、审批保护、SLA 和外部 MES/QMS 同步
│   │   │   ├── purchase_service.py           # 采购申请创建、字段校验、审批保护和 ERP 同步
│   │   │   ├── approval_service.py           # 兼容版审批服务，审批通过后执行业务动作
│   │   │   ├── approval_engine.py            # 多级审批引擎，支持模板路由、会签/或签、动作记录
│   │   │   ├── approval_guard.py             # 高风险写入保护，防止绕过审批直接写业务表
│   │   │   ├── audit_service.py              # 审计日志写入、查询、分页
│   │   │   ├── business_sync_service.py      # 业务对象同步外部系统并记录 external_id_mapping
│   │   │   ├── permission_service.py         # 用户角色、数据范围、文档权限判断
│   │   │   ├── sla_service.py                # SLA 策略匹配、实例创建、状态更新
│   │   │   └── llm_service.py                # OpenAI-compatible LLM 调用封装

│   │   ├── integrations/                     # 企业集成层
│   │   │   ├── __init__.py                   # integrations 包标识
│   │   │   ├── core/                         # 集成抽象和通用结构
│   │   │   │   ├── __init__.py               # core 包标识
│   │   │   │   ├── base.py                   # Provider 抽象：通知、登录、组织、审批、业务系统
│   │   │   │   ├── schemas.py                # 集成层通用数据结构
│   │   │   │   ├── registry.py               # 根据平台选择 local/wecom/dingtalk/feishu provider
│   │   │   │   ├── exceptions.py             # 集成异常类型
│   │   │   │   └── idempotency.py            # 回调、通知、外部写入幂等处理
│   │   │   ├── providers/                    # 不同平台适配器
│   │   │   │   ├── __init__.py               # providers 包标识
│   │   │   │   ├── local.py                  # 本地演示 provider
│   │   │   │   ├── generic_webhook.py        # 通用 Webhook 通知 provider
│   │   │   │   ├── wecom.py                  # 企业微信 provider，占位真实接口和本地降级逻辑
│   │   │   │   ├── dingtalk.py               # 钉钉 provider，占位真实接口和本地降级逻辑
│   │   │   │   ├── feishu.py                 # 飞书 provider，占位真实接口和本地降级逻辑
│   │   │   │   ├── generic_oa.py             # 通用 OA 适配，支持任务同步
│   │   │   │   ├── generic_erp.py            # 通用 ERP 适配，支持采购申请同步
│   │   │   │   ├── generic_mes.py            # 通用 MES 适配，支持维修/质量工单同步
│   │   │   │   └── generic_wms.py            # 通用 WMS 适配，预留库存/物料查询同步
│   │   │   ├── services/                     # 集成编排服务
│   │   │   │   ├── __init__.py               # integration services 包标识
│   │   │   │   ├── notification_service.py   # 统一通知服务，发送并记录 notification_delivery
│   │   │   │   ├── org_sync_service.py       # 组织架构同步，落库 departments/users/external mappings
│   │   │   │   ├── sso_service.py            # 企业登录和外部用户身份转换
│   │   │   │   ├── approval_bridge_service.py# 外部审批桥接，创建外部审批并处理状态回写
│   │   │   │   ├── business_sync_service.py  # 外部业务系统同步封装
│   │   │   │   └── sla_escalation_service.py # SLA 提醒、超时、升级通知
│   │   │   └── callbacks/                    # 平台回调解析
│   │   │       ├── __init__.py               # callbacks 包标识
│   │   │       ├── wecom_callback.py         # 企业微信回调验签/解析/内部事件转换
│   │   │       ├── dingtalk_callback.py      # 钉钉回调验签/解析/内部事件转换
│   │   │       └── feishu_callback.py        # 飞书回调验签/解析/内部事件转换

│   │   ├── jobs/                             # 异步任务和失败重试
│   │   │   ├── __init__.py                   # jobs 包标识
│   │   │   ├── worker.py                     # RQ/Redis Worker 入口和任务注册
│   │   │   ├── notification_jobs.py          # 通知发送重试任务
│   │   │   ├── org_sync_jobs.py              # 组织架构同步任务
│   │   │   ├── sla_jobs.py                   # SLA 扫描、提醒、超时、关闭任务
│   │   │   ├── business_sync_jobs.py         # 外部业务系统同步重试任务
│   │   │   └── cleanup_jobs.py               # 过期事件、通知记录、幂等键清理任务

│   │   ├── rag/                              # RAG 知识库模块
│   │   │   ├── __init__.py                   # rag 包标识
│   │   │   ├── document_loader.py            # PDF、DOCX、TXT、Markdown 文档解析
│   │   │   ├── text_splitter.py              # 中文友好的文档切块和重叠处理
│   │   │   ├── embedding_client.py           # Embedding 客户端，支持真实 API 和本地演示向量
│   │   │   ├── vector_store.py               # pgvector 写入、检索和权限过滤
│   │   │   ├── retriever.py                  # 根据问题检索相关 chunk，并带文档权限过滤
│   │   │   ├── reranker.py                   # 检索结果重排
│   │   │   └── prompt_builder.py             # 构造带引用来源的回答 Prompt

│   │   ├── agents/                           # Agent 编排模块
│   │   │   ├── __init__.py                   # agents 包标识
│   │   │   ├── factory_office_agent.py       # Agent 总入口，优先 LangGraph，失败走本地降级
│   │   │   ├── graph_state.py                # Agent 状态定义
│   │   │   ├── graph_nodes.py                # 意图识别、知识检索、补槽、工具选择、审批判断节点
│   │   │   ├── graph_edges.py                # LangGraph 路由边逻辑
│   │   │   ├── prompts.py                    # 制造业 Agent 提示词
│   │   │   ├── task_state.py                 # Agent 任务状态机
│   │   │   ├── sop_registry.py               # SOP 匹配入口
│   │   │   ├── slot_filling.py               # 多轮补槽和缺字段追问
│   │   │   └── trace.py                      # Agent 执行轨迹记录

│   │   ├── workflows/                        # 固定办公流程模块
│   │   │   ├── __init__.py                   # workflows 包标识
│   │   │   ├── meeting_to_tasks.py           # 会议纪要转任务草稿
│   │   │   ├── maintenance_ticket.py         # 设备异常转维修工单草稿
│   │   │   ├── quality_issue.py              # 质量异常转 NCR/质量工单草稿
│   │   │   ├── purchase_request.py           # 采购需求转采购申请草稿
│   │   │   ├── weekly_report.py              # 项目记录转周报草稿
│   │   │   └── sop_definitions.py            # SOP 定义和必填槽位

│   │   ├── tools/                            # Agent 可调用工具层
│   │   │   ├── __init__.py                   # tools 包标识
│   │   │   ├── base.py                       # 工具统一结构、风险等级、审批策略
│   │   │   ├── knowledge_tools.py            # 知识库搜索工具
│   │   │   ├── task_tools.py                 # 任务创建和查询工具
│   │   │   ├── ticket_tools.py               # 工单草稿、创建工单、查询工单工具
│   │   │   ├── purchase_tools.py             # 采购申请草稿、创建采购、查询采购工具
│   │   │   ├── approval_tools.py             # 审批创建和状态查询工具
│   │   │   └── notification_tools.py         # 通知/邮件草稿工具

│   │   ├── evaluators/                       # RAG 和工作流评测模块
│   │   │   ├── rag_eval.py                   # 知识库问答评测
│   │   │   ├── workflow_eval.py              # 工作流输出评测
│   │   │   └── test_cases.py                 # 制造业评测用例集合

│   │   └── utils/                            # 后端通用工具
│   │       ├── __init__.py                   # utils 包标识
│   │       ├── file_utils.py                 # 文件名清洗、扩展名校验、哈希、删除文件
│   │       ├── time_utils.py                 # 时间格式化、当前时间、日期处理
│   │       ├── json_utils.py                 # JSON 安全解析、序列化、字段提取
│   │       └── id_utils.py                   # UUID、业务 ID、追踪 ID 生成

│   ├── alembic/                              # 数据库迁移目录
│   │   ├── README                            # Alembic 目录说明
│   │   ├── env.py                            # Alembic 环境，加载模型元数据
│   │   ├── script.py.mako                    # 迁移脚本模板
│   │   └── versions/
│   │       ├── 20260502_0001_initial_schema.py                  # 初始化业务表和 pgvector
│   │       ├── 20260525_0002_enterprise_integration_schema.py   # 企业集成、组织、角色、通知、SLA 基础表
│   │       ├── 20260525_0003_approval_engine_schema.py          # 多级审批引擎表
│   │       ├── 20260525_0004_document_permissions_schema.py     # 文档权限表和检索权限字段
│   │       ├── 20260525_0005_external_mapping_nullable_external_id.py # 外部 ID 映射兼容调整
│   │       └── 20260525_0006_notification_payload_snapshot.py   # 通知 payload 快照字段

│   ├── tests/                                # 后端测试
│   │   ├── test_health.py                    # 健康检查测试
│   │   ├── test_document_upload.py           # 文档上传、解析、限制、去重测试
│   │   ├── test_rag_search.py                # RAG 检索测试
│   │   ├── test_knowledge_ask.py             # 知识库问答和引用来源测试
│   │   ├── test_workflows.py                 # 办公工作流测试
│   │   ├── test_quality_issue_workflow.py    # 质量异常工作流测试
│   │   ├── test_approvals.py                 # 兼容审批流程测试
│   │   ├── test_approval_engine.py           # 多级审批引擎测试
│   │   ├── test_approval_template_routing.py # 按金额/业务类型选择审批模板测试
│   │   ├── test_agent_routes.py              # Agent 意图、SOP、补槽、Trace 路由测试
│   │   ├── test_security.py                  # 权限和高风险接口测试
│   │   ├── test_seed_demo_data.py            # seed 数据导入测试
│   │   ├── test_ingest_demo_docs.py          # demo 文档解析和切块导入测试
│   │   ├── test_enterprise_models.py         # 企业、部门、角色等模型测试
│   │   ├── test_integration_configs.py       # 企业集成配置测试
│   │   ├── test_integration_core.py          # 集成核心抽象测试
│   │   ├── test_integration_providers.py     # wecom/dingtalk/feishu/local provider 测试
│   │   ├── test_integration_services.py      # 集成服务编排测试
│   │   ├── test_integration_callbacks.py     # 平台回调解析测试
│   │   ├── test_generic_webhook_provider.py  # 通用 Webhook provider 测试
│   │   ├── test_notification_service.py      # 通知服务和发送记录测试
│   │   ├── test_org_sync_service.py          # 组织同步落库测试
│   │   ├── test_callback_idempotency.py      # 回调幂等测试
│   │   ├── test_sla_escalation.py            # SLA 提醒和升级测试
│   │   ├── test_sla_auto_creation.py         # 工单/采购自动创建 SLA 实例测试
│   │   ├── test_external_id_mapping.py       # 外部 ID 映射测试
│   │   ├── test_document_permissions.py      # 文档权限模型测试
│   │   ├── test_document_permission_filter.py# RAG 检索权限过滤测试
│   │   ├── test_business_sync_service.py     # 外部业务同步服务测试
│   │   ├── test_business_sync_records.py     # 外部同步记录落库测试
│   │   └── test_jobs.py                      # 异步任务函数测试

│   ├── requirements.txt                      # 后端运行依赖
│   ├── requirements-dev.txt                  # 后端开发和测试依赖
│   ├── Dockerfile                            # 后端 Docker 镜像
│   ├── .dockerignore                         # 后端 Docker 忽略规则
│   └── alembic.ini                           # Alembic 配置文件

├── frontend/                                 # Vue3 + Element Plus 前端
│   ├── src/
│   │   ├── main.ts                           # 前端入口，挂载 Vue、路由和 Element Plus
│   │   ├── App.vue                           # 根组件，定义整体布局和侧边栏
│   │   ├── env.d.ts                          # Vite/TypeScript 类型声明
│   │   ├── router/index.ts                   # 页面路由和菜单配置
│   │   ├── api/
│   │   │   ├── http.ts                       # Axios 实例和错误处理
│   │   │   ├── documents.ts                  # 文档接口封装
│   │   │   ├── knowledge.ts                  # 知识库接口封装
│   │   │   ├── agent.ts                      # Agent 对话接口封装
│   │   │   ├── workflows.ts                  # 工作流接口封装
│   │   │   ├── tasks.ts                      # 任务接口封装
│   │   │   ├── tickets.ts                    # 工单接口封装
│   │   │   ├── purchases.ts                  # 采购接口封装
│   │   │   ├── approvals.ts                  # 审批接口封装
│   │   │   ├── approvalTemplates.ts          # 审批模板接口封装
│   │   │   ├── auditLogs.ts                  # 审计日志接口封装
│   │   │   ├── integrations.ts               # 企业集成配置接口封装
│   │   │   └── sla.ts                        # SLA 接口封装
│   │   ├── views/
│   │   │   ├── DashboardView.vue             # 首页仪表盘
│   │   │   ├── KnowledgeBaseView.vue         # 知识库上传、问答和引用来源页面
│   │   │   ├── AgentChatView.vue             # Agent 对话、SOP、Trace 展示页面
│   │   │   ├── WorkflowsView.vue             # 办公流程页面
│   │   │   ├── TasksView.vue                 # 任务页面
│   │   │   ├── TicketsView.vue               # 工单页面
│   │   │   ├── PurchasesView.vue             # 采购申请页面
│   │   │   ├── ApprovalsView.vue             # 审批处理页面
│   │   │   ├── ApprovalTemplatesView.vue     # 审批模板配置页面
│   │   │   ├── AuditLogsView.vue             # 审计日志页面
│   │   │   ├── IntegrationSettingsView.vue   # 企业微信/钉钉/飞书/Webhook 集成配置页
│   │   │   ├── OrgSyncView.vue               # 组织架构同步页面
│   │   │   ├── SlaSettingsView.vue           # SLA 策略配置页面
│   │   │   └── MobileApprovalView.vue        # H5 移动审批详情和处理页面
│   │   ├── components/.gitkeep               # 预留公共组件目录
│   │   ├── stores/.gitkeep                   # 预留前端状态目录
│   │   ├── types/.gitkeep                    # 预留 TypeScript 类型目录
│   │   └── utils/.gitkeep                    # 预留前端工具目录
│   ├── public/.gitkeep                       # 静态资源目录占位
│   ├── index.html                            # Vite HTML 入口
│   ├── package.json                          # 前端依赖和脚本
│   ├── package-lock.json                     # 前端依赖锁定文件
│   ├── vite.config.ts                        # Vite 配置
│   ├── tsconfig.json                         # TypeScript 配置
│   ├── nginx.conf                            # 前端容器 Nginx 配置
│   ├── Dockerfile                            # 前端 Docker 镜像
│   └── .dockerignore                         # 前端 Docker 忽略规则

├── data/                                     # 演示数据与上传目录
│   ├── demo_docs/                            # 制造业模拟知识库文档
│   │   ├── .gitkeep                          # 保留目录
│   │   ├── 采购管理制度.md                   # 采购制度示例
│   │   ├── 差旅报销制度.md                   # 差旅报销制度示例
│   │   ├── 设备维修手册_空压机.md            # 空压机维修手册示例
│   │   ├── 质量异常处理流程.md               # 质量异常/NCR 流程示例
│   │   ├── 安全生产规范.md                   # 安全生产规范示例
│   │   └── 项目周报模板.md                   # 项目周报模板示例
│   ├── seed/                                 # 初始化业务数据
│   │   ├── enterprises.json                  # 演示企业/租户数据
│   │   ├── departments.json                  # 演示部门数据
│   │   ├── roles.json                        # 演示角色数据
│   │   ├── user_roles.json                   # 演示用户角色关系
│   │   ├── users.json                        # 演示用户数据
│   │   ├── tasks.json                        # 演示任务数据
│   │   ├── tickets.json                      # 演示工单数据
│   │   ├── purchase_requests.json            # 演示采购申请数据
│   │   ├── approvals.json                    # 演示兼容审批数据
│   │   ├── approval_templates.json           # 演示审批模板数据
│   │   ├── approval_steps.json               # 演示审批步骤数据
│   │   ├── integration_configs.json          # 演示集成配置数据
│   │   ├── sla_policies.json                 # 演示 SLA 策略数据
│   │   └── audit_logs.json                   # 演示审计日志数据
│   └── uploads/.gitkeep                      # 本地上传目录占位，不提交真实上传文件

├── docs/                                     # 项目文档
│   ├── architecture.md                       # 系统架构说明
│   ├── api.md                                # API 说明
│   ├── database.md                           # 数据库设计说明
│   ├── rag_design.md                         # RAG 设计说明
│   ├── workflow_design.md                    # 工作流设计说明
│   ├── agent_design.md                       # Agent 编排设计说明
│   ├── demo_script.md                        # 演示脚本
│   ├── roadmap.md                            # 后续计划
│   ├── deploy_enterprise.md                  # 企业部署说明
│   ├── enterprise_integration_design.md      # 企业集成层设计
│   ├── integration_wecom.md                  # 企业微信集成说明
│   ├── integration_dingtalk.md               # 钉钉集成说明
│   ├── integration_feishu.md                 # 飞书集成说明
│   └── security_checklist.md                 # 安全检查清单

├── scripts/                                  # 项目辅助脚本
│   ├── seed_demo_data.py                     # 导入 data/seed/*.json 到数据库
│   └── ingest_demo_docs.py                   # 批量导入 demo_docs，解析、切块、向量化、入库

├── .env.example                              # 基础环境变量模板
├── .env.example.enterprise                   # 企业部署环境变量模板
├── .gitignore                                # Git 忽略规则
├── docker-compose.yml                        # 本地演示 Docker Compose
├── docker-compose.enterprise.yml             # 企业部署 Docker Compose
├── README.md                                 # GitHub 首页说明
├── SUPERVISOR_COMPATIBILITY.md               # 面向业务负责人/管理层的说明
└── LICENSE                                   # 权利保留许可声明

```

说明：

- `.env` 是本地运行配置文件，不提交到代码仓库。
- `.venv/`、`frontend/node_modules/`、`frontend/dist/`、`__pycache__/` 属于本地开发或构建产物，不属于项目源码结构。
- `00_project_truth/` 是项目唯一真源目录，当前只保留 `PROJECT_SSOT.md`。
- `SUPERVISOR_COMPATIBILITY.md` 位于项目根目录，用于面向业务和管理人员说明项目价值、使用场景和风险边界。

## 快速启动

复制环境变量模板：

```bash
cp .env.example .env
```

启动服务：

```bash
docker compose up -d
```

访问地址：

```text
前端：http://localhost:3000
后端：http://localhost:8000
接口文档：http://localhost:8000/docs
健康检查：http://localhost:8000/api/health
```

健康检查预期返回：

```json
{
  "status": "ok"
}
```

## 导入演示数据

初始化业务数据：

```bash
DATABASE_URL=postgresql+psycopg://factory_user:factory_pass@localhost:5432/factory_agent \
PYTHONPATH=backend .venv/bin/python scripts/seed_demo_data.py
```

导入演示文档并生成切块和本地演示向量：

```bash
DATABASE_URL=postgresql+psycopg://factory_user:factory_pass@localhost:5432/factory_agent \
PYTHONPATH=backend .venv/bin/python scripts/ingest_demo_docs.py
```

如果配置了真实 Embedding API，可使用：

```bash
DATABASE_URL=postgresql+psycopg://factory_user:factory_pass@localhost:5432/factory_agent \
PYTHONPATH=backend .venv/bin/python scripts/ingest_demo_docs.py --real-embedding
```

## 推荐验证流程

1. 打开首页仪表盘，查看文档、任务、工单、审批和审计数据。
2. 在知识库页面查看或上传制造业制度文档。
3. 提问“采购金额超过 5 万需要谁审批？”并检查引用来源。
4. 输入空压机 E07 报警场景，生成维修工单草稿。
5. 输入质量异常场景，生成质量异常工单草稿。
6. 输入采购需求，生成采购申请草稿。
7. 输入会议纪要，生成任务草稿。
8. 在审批页面批准或拒绝待执行动作。
9. 在任务、工单、采购页面确认业务对象是否按审批结果写入。
10. 在审计日志页面查看工具参数和执行结果。

## 权限和安全边界

当前版本提供本地演示登录，登录后优先使用 Bearer token 识别角色：

```text
Authorization: Bearer <access_token>
```

为了方便本地调试，仍兼容请求头角色：

```text
X-User-Role: manager
```

规则：

- 普通员工可以查询知识库、上传文档、生成流程草稿。
- 主管或管理员可以查看审批、批准审批、拒绝审批、查看审计日志、申请删除文档。
- 高风险动作先进入 approvals 表。
- 审批通过后才写入正式业务表。

当前版本已经提供企业集成抽象、通用 webhook、通知投递记录、SLA、组织同步和外部业务系统同步骨架；企业微信、钉钉、飞书默认按通知/签名 H5 审批链接模式接入。生产使用前仍需要按企业实际开放平台权限、回调验签、组织权限和外部系统 API 做配置与联调，不处理真实企业敏感文件，不替代质量、安全、财务等责任岗位的最终判断。

## 文档

- 唯一真源：[`00_project_truth/PROJECT_SSOT.md`](00_project_truth/PROJECT_SSOT.md)
- 业务与管理层说明：[`SUPERVISOR_COMPATIBILITY.md`](SUPERVISOR_COMPATIBILITY.md)
- 架构说明：[`docs/architecture.md`](docs/architecture.md)
- API 说明：[`docs/api.md`](docs/api.md)
- 数据库设计：[`docs/database.md`](docs/database.md)
- RAG 设计：[`docs/rag_design.md`](docs/rag_design.md)
- 工作流设计：[`docs/workflow_design.md`](docs/workflow_design.md)
- Agent 设计：[`docs/agent_design.md`](docs/agent_design.md)

## 当前限制

- 当前登录是本地演示 token，不是生产级统一认证或完整 SSO。
- 当前文件存储使用本地 uploads 目录，不是生产级对象存储。
- 当前本地演示向量用于无 API Key 场景，正式知识库应配置真实 Embedding 服务。
- 当前工作流为固定流程，不是让 Agent 自由执行所有企业动作。
- 当前只开放设备维修和质量异常两类工单的新建流程。

## License

Copyright (c) 2026 xhlnga. All rights reserved.

本项目源代码仅用于公开展示、技术评估和学习参考。未经作者书面许可，任何个人或组织不得复制、修改、分发、商用、部署，或基于本项目创建衍生作品。

如需使用、部署、二次开发、商业合作或在企业内部试点，请先联系作者取得授权。
