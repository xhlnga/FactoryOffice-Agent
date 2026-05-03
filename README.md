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

## 为什么说它高度拟真

项目的拟真点不只是文档内容，而是业务机制和工程结构。

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

### 5. 有可替换的外部系统边界

当前版本用数据库模拟任务系统、工单系统、采购申请系统、审批系统和日志系统。后续可以把 tools 层替换为真实 OA、ERP、MES 或即时通讯平台接口。

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
│   └── PROJECT_SSOT.md                       # 项目唯一真源，定义项目定位、功能边界、技术栈、工作流、风险约束和不做什么

├── backend/                                  # FastAPI 后端服务
│   ├── app/                                  # 后端主应用代码
│   │   ├── __init__.py                       # Python 包标识
│   │   ├── main.py                           # FastAPI 入口，创建应用、挂载 API 路由、配置 CORS、注册异常处理

│   │   ├── api/                              # HTTP API 路由层
│   │   │   ├── __init__.py                   # API 包标识
│   │   │   └── v1/                           # API v1 版本目录
│   │   │       ├── __init__.py               # v1 包标识
│   │   │       ├── router.py                 # API v1 总路由，统一注册 health、documents、knowledge、agent、workflows 等接口
│   │   │       └── endpoints/                # 具体业务接口
│   │   │           ├── __init__.py           # endpoints 包标识
│   │   │           ├── health.py             # 健康检查接口，返回后端服务状态
│   │   │           ├── auth.py               # 本地身份模拟接口，返回模拟用户和角色信息
│   │   │           ├── documents.py          # 文档上传、文档列表、文档入库、文档删除审批申请
│   │   │           ├── knowledge.py          # 知识库检索和知识库问答接口，返回引用来源
│   │   │           ├── agent.py              # 通用 Agent 对话入口，执行意图识别、SOP 匹配、补槽、工具预览和审计记录
│   │   │           ├── workflows.py          # 固定办公流程接口，包含会议、维修、质量、采购、周报
│   │   │           ├── tasks.py              # 任务列表、任务详情、创建任务审批申请
│   │   │           ├── tickets.py            # 工单列表、工单详情、创建设备维修/质量异常工单审批申请
│   │   │           ├── purchases.py          # 采购申请列表、详情、创建采购申请审批申请
│   │   │           ├── approvals.py          # 审批列表、待审批列表、批准审批、拒绝审批
│   │   │           └── audit_logs.py         # 审计日志列表和详情查询

│   │   ├── core/                             # 后端基础设施层
│   │   │   ├── __init__.py                   # core 包标识
│   │   │   ├── config.py                     # 读取环境变量，管理数据库、上传目录、LLM、Embedding、CORS、上传大小限制
│   │   │   ├── database.py                   # SQLAlchemy Engine、SessionLocal、Base、数据库依赖注入
│   │   │   ├── security.py                   # 本地角色权限控制，区分 employee、manager、admin
│   │   │   ├── logging.py                    # 后端日志格式、日志级别和日志初始化
│   │   │   └── exceptions.py                 # 统一业务异常 AppException 和 FastAPI 异常处理

│   │   ├── models/                           # SQLAlchemy 数据库模型
│   │   │   ├── __init__.py                   # 模型统一导入
│   │   │   ├── base.py                       # Base、通用时间字段、角色/状态/优先级枚举
│   │   │   ├── user.py                       # users 用户表，用于本地身份模拟和后续权限扩展
│   │   │   ├── document.py                   # documents 文档表，记录文件名、分类、路径、哈希、软删除时间
│   │   │   ├── document_chunk.py             # document_chunks 文档切块表，保存 chunk 文本、元数据和 pgvector 向量
│   │   │   ├── task.py                       # tasks 任务表，用于会议纪要转任务后的正式任务记录
│   │   │   ├── ticket.py                     # tickets 工单表，用于设备维修和质量异常工单
│   │   │   ├── purchase_request.py           # purchase_requests 采购申请表，记录物品、数量、用途、预算、供应商和状态
│   │   │   ├── approval.py                   # approvals 审批表，记录待确认动作、参数、审批人、结果和执行状态
│   │   │   └── audit_log.py                  # audit_logs 审计日志表，记录用户输入、工具参数、输出和执行状态

│   │   ├── schemas/                          # Pydantic 请求和响应结构
│   │   │   ├── __init__.py                   # schemas 包标识
│   │   │   ├── common.py                     # 通用响应、分页响应等基础结构
│   │   │   ├── user.py                       # 用户、登录、本地身份模拟相关结构
│   │   │   ├── document.py                   # 文档上传、文档读取、文档切块展示结构
│   │   │   ├── knowledge.py                  # 知识库搜索、问答、检索结果、引用来源结构
│   │   │   ├── agent.py                      # Agent 请求、响应、工具调用预览、缺失字段、Trace 结构
│   │   │   ├── workflow.py                   # 会议、维修、质量、采购、周报工作流输入输出结构
│   │   │   ├── task.py                       # 任务创建、更新、读取结构
│   │   │   ├── ticket.py                     # 工单创建、更新、读取结构
│   │   │   ├── purchase_request.py           # 采购申请创建、更新、读取结构
│   │   │   ├── approval.py                   # 审批创建、审批读取、批准/拒绝请求结构
│   │   │   └── audit_log.py                  # 审计日志读取和创建结构

│   │   ├── services/                         # 业务服务层
│   │   │   ├── __init__.py                   # services 包标识
│   │   │   ├── document_service.py           # 文档分块保存、大小限制、哈希去重、解析入库、软删除
│   │   │   ├── knowledge_service.py          # 串联检索、Prompt、LLM 回答和引用来源，未配置模型时提供抽取式兜底
│   │   │   ├── task_service.py               # 任务创建、查询、分页、更新，写入前受审批保护
│   │   │   ├── ticket_service.py             # 工单创建、查询、分页、更新，写入前受审批保护
│   │   │   ├── purchase_service.py           # 采购申请创建、查询、分页、更新，审批后进入待采购审批状态
│   │   │   ├── approval_service.py           # 创建审批、批准审批、拒绝审批、审批通过后执行业务动作并写审计
│   │   │   ├── approval_guard.py             # 高风险写入保护，防止绕过审批直接写任务、工单、采购、文档删除
│   │   │   ├── audit_service.py              # 审计日志创建、查询、分页和详情
│   │   │   └── llm_service.py                # OpenAI-compatible Chat Completions 调用封装

│   │   ├── rag/                              # RAG 知识库模块
│   │   │   ├── __init__.py                   # rag 包标识
│   │   │   ├── document_loader.py            # PDF、DOCX、TXT、Markdown 文档解析为纯文本
│   │   │   ├── text_splitter.py              # 中文友好的文档切块和重叠处理
│   │   │   ├── embedding_client.py           # Embedding 客户端，支持真实 API 和本地确定性演示向量
│   │   │   ├── vector_store.py               # pgvector 存储、向量字段封装、相似度检索和 chunk 写入
│   │   │   ├── retriever.py                  # 根据用户问题检索相关文档片段
│   │   │   ├── reranker.py                   # 检索结果重排，优先保留业务相关片段
│   │   │   └── prompt_builder.py             # 构造带引用来源的 RAG Prompt 和引用标签

│   │   ├── agents/                           # Agent 编排模块
│   │   │   ├── __init__.py                   # agents 包标识
│   │   │   ├── factory_office_agent.py       # Agent 总入口，优先编译 LangGraph，失败时使用本地降级流程
│   │   │   ├── graph_state.py                # Agent 状态定义，包含输入、意图、SOP、槽位、工具、审批、Trace
│   │   │   ├── graph_nodes.py                # 意图识别、知识检索、补槽、工具选择、审批判断、最终回答节点
│   │   │   ├── graph_edges.py                # LangGraph 边逻辑，根据意图和审批状态决定下一步节点
│   │   │   ├── prompts.py                    # 制造业 Agent 系统提示词和任务提示词
│   │   │   ├── task_state.py                 # Agent 任务状态机，定义 collecting_info、waiting_approval、completed 等状态
│   │   │   ├── sop_registry.py               # 根据意图匹配 SOP，并把 SOP 摘要转换为 Trace 信息
│   │   │   ├── slot_filling.py               # 多轮补槽逻辑，合并上下文、提取字段、生成缺字段追问
│   │   │   └── trace.py                      # Agent 执行轨迹工具，记录每一步节点状态和细节

│   │   ├── workflows/                        # 固定办公流程模块
│   │   │   ├── __init__.py                   # workflows 包标识
│   │   │   ├── meeting_to_tasks.py           # 从会议纪要中提取任务草稿、负责人、截止时间和优先级
│   │   │   ├── maintenance_ticket.py         # 根据设备异常生成维修工单草稿和排查建议
│   │   │   ├── quality_issue.py              # 根据质量异常描述生成 NCR/质量异常工单草稿
│   │   │   ├── purchase_request.py           # 从采购需求中提取物品、数量、用途、预算、供应商并提示缺失字段
│   │   │   ├── weekly_report.py              # 根据项目记录生成周报草稿
│   │   │   └── sop_definitions.py            # 定义知识问答、会议、维修、质量、采购、周报 SOP 和必填槽位

│   │   ├── tools/                            # Agent 可调用工具层
│   │   │   ├── __init__.py                   # tools 包标识
│   │   │   ├── base.py                       # 工具统一结构、风险等级、审批策略和工具结果结构
│   │   │   ├── knowledge_tools.py            # 知识库搜索工具封装
│   │   │   ├── task_tools.py                 # 创建任务、批量任务审批载荷和任务查询工具
│   │   │   ├── ticket_tools.py               # 维修/质量工单草稿、创建工单审批载荷和工单查询工具
│   │   │   ├── purchase_tools.py             # 采购申请草稿、创建采购审批载荷和采购查询工具
│   │   │   ├── approval_tools.py             # 创建审批记录、审批状态查询相关工具
│   │   │   └── notification_tools.py         # 通知/邮件草稿工具，当前只生成草稿不真实发送

│   │   ├── evaluators/                       # RAG 和工作流评测模块
│   │   │   ├── rag_eval.py                   # RAG 回答评测，检查引用来源、空答案和占位回答风险
│   │   │   ├── workflow_eval.py              # 工作流评测，检查草稿字段完整性和审批边界
│   │   │   └── test_cases.py                 # 制造业场景评测用例集合

│   │   └── utils/                            # 后端通用工具函数
│   │       ├── __init__.py                   # utils 包标识
│   │       ├── file_utils.py                 # 文件名清洗、扩展名校验、SHA256、删除文件等工具
│   │       ├── time_utils.py                 # 当前时间、日期时间格式化等工具
│   │       ├── json_utils.py                 # JSON 安全解析、序列化和字典字段提取工具
│   │       └── id_utils.py                   # UUID、业务 ID、追踪 ID 生成工具

│   ├── alembic/                              # 数据库迁移目录
│   │   ├── README                            # Alembic 目录说明
│   │   ├── env.py                            # Alembic 运行环境，加载数据库配置和模型元数据
│   │   ├── script.py.mako                    # Alembic 迁移脚本模板
│   │   └── versions/
│   │       └── 20260502_0001_initial_schema.py # 初始化 pgvector 扩展、业务表、枚举和索引

│   ├── tests/                                # 后端测试
│   │   ├── test_health.py                    # 健康检查测试
│   │   ├── test_document_upload.py           # 上传、解析、大小限制、去重、软删除测试
│   │   ├── test_rag_search.py                # RAG 检索和知识工具测试
│   │   ├── test_knowledge_ask.py             # 知识库问答和引用来源测试
│   │   ├── test_workflows.py                 # 会议、维修、采购、周报工作流测试
│   │   ├── test_quality_issue_workflow.py    # 质量异常工作流测试
│   │   ├── test_approvals.py                 # 审批创建、批准、拒绝、执行动作测试
│   │   ├── test_agent_routes.py              # Agent 意图识别、SOP、补槽、Trace 和路由测试
│   │   ├── test_security.py                  # 本地角色权限和高风险接口访问测试
│   │   ├── test_seed_demo_data.py            # seed JSON 数据结构和导入逻辑测试
│   │   └── test_ingest_demo_docs.py          # demo 文档解析、切块和批量导入测试

│   ├── requirements.txt                      # 后端运行依赖
│   ├── requirements-dev.txt                  # 后端开发和测试依赖
│   ├── Dockerfile                            # 后端 Docker 镜像构建文件
│   ├── .dockerignore                         # 后端 Docker 构建忽略规则
│   └── alembic.ini                           # Alembic 配置文件

├── frontend/                                 # Vue3 + Element Plus 前端
│   ├── src/                                  # 前端源码
│   │   ├── main.ts                           # Vue 应用入口，挂载 App、路由和 Element Plus
│   │   ├── App.vue                           # 根组件，定义左侧菜单、顶部栏和整体页面布局
│   │   ├── env.d.ts                          # Vite 和 TypeScript 环境类型声明
│   │   ├── router/
│   │   │   └── index.ts                      # 页面路由配置和左侧菜单来源
│   │   ├── api/
│   │   │   ├── http.ts                       # Axios 实例、baseURL、请求拦截器和错误标准化
│   │   │   ├── documents.ts                  # 文档上传、列表、切块、删除申请接口封装
│   │   │   ├── knowledge.ts                  # 知识库搜索和问答接口封装
│   │   │   ├── agent.ts                      # Agent 对话接口、SOP、Trace、工具调用类型
│   │   │   ├── workflows.ts                  # 会议、维修、质量、采购、周报流程接口封装
│   │   │   ├── tasks.ts                      # 任务列表、详情、创建审批申请接口封装
│   │   │   ├── tickets.ts                    # 工单列表、详情、创建审批申请接口封装
│   │   │   ├── purchases.ts                  # 采购申请列表、详情、创建审批申请接口封装
│   │   │   ├── approvals.ts                  # 审批列表、待审批、批准、拒绝接口封装
│   │   │   └── auditLogs.ts                  # 审计日志列表和详情接口封装
│   │   ├── views/
│   │   │   ├── DashboardView.vue             # 首页仪表盘，展示文档、任务、工单、采购、审批和最近审计记录
│   │   │   ├── KnowledgeBaseView.vue         # 知识库页面，支持上传文档、查看列表、提问和展示引用来源
│   │   │   ├── AgentChatView.vue             # AI 助手页面，展示意图、SOP、任务状态、缺失字段、工具预览和 Trace
│   │   │   ├── WorkflowsView.vue             # 办公流程页面，支持会议、维修、质量、采购、周报草稿生成
│   │   │   ├── TasksView.vue                 # 任务页面，展示任务列表、详情和任务创建审批申请
│   │   │   ├── TicketsView.vue               # 工单页面，展示设备维修和质量异常工单
│   │   │   ├── PurchasesView.vue             # 采购申请页面，展示采购申请列表和详情
│   │   │   ├── ApprovalsView.vue             # 审批页面，支持查看待审批动作、批准和拒绝
│   │   │   └── AuditLogsView.vue             # 审计日志页面，展示用户输入、工具参数和执行结果
│   │   ├── components/
│   │   │   └── .gitkeep                      # 预留组件目录，后续拆分公共组件
│   │   ├── stores/
│   │   │   └── .gitkeep                      # 预留状态目录，后续接入全局状态管理
│   │   ├── types/
│   │   │   └── .gitkeep                      # 预留类型目录，后续集中管理 TypeScript 类型
│   │   └── utils/
│   │       └── .gitkeep                      # 预留前端工具目录

│   ├── public/
│   │   └── .gitkeep                          # 前端静态资源目录占位
│   ├── index.html                            # Vite HTML 入口
│   ├── package.json                          # 前端依赖和 npm 脚本
│   ├── package-lock.json                     # 前端依赖锁定文件
│   ├── vite.config.ts                        # Vite 配置、端口和 API 代理
│   ├── tsconfig.json                         # TypeScript 配置
│   ├── Dockerfile                            # 前端 Docker 镜像构建文件
│   └── .dockerignore                         # 前端 Docker 构建忽略规则

├── data/                                     # 演示数据与上传目录
│   ├── demo_docs/
│   │   ├── .gitkeep                          # 保留目录
│   │   ├── 采购管理制度.md                   # 采购金额阈值、审批权限、供应商和归档规则演示文档
│   │   ├── 差旅报销制度.md                   # 差旅申请、报销标准、票据要求和审批规则演示文档
│   │   ├── 设备维修手册_空压机.md            # 空压机报警、点检、维修和安全排查演示文档
│   │   ├── 质量异常处理流程.md               # 质量异常、隔离、复检、NCR 和关闭流程演示文档
│   │   ├── 安全生产规范.md                   # 安全作业、动火审批、隐患处置和事故上报演示文档
│   │   └── 项目周报模板.md                   # 周报结构、风险项、决策事项和下周计划模板
│   ├── seed/
│   │   ├── users.json                        # 演示用户、角色、部门数据
│   │   ├── tasks.json                        # 演示任务数据
│   │   ├── tickets.json                      # 演示设备维修和质量异常工单数据
│   │   ├── purchase_requests.json            # 演示采购申请数据
│   │   ├── approvals.json                    # 演示审批记录
│   │   └── audit_logs.json                   # 演示审计日志记录
│   └── uploads/
│       └── .gitkeep                          # 保留上传目录，不提交真实上传文件

├── docs/                                     # 普通项目文档
│   ├── architecture.md                       # 系统架构、模块分层、数据流和部署说明
│   ├── api.md                                # 后端 API 说明和接口边界
│   ├── database.md                           # 数据库实体、字段和关系说明
│   ├── rag_design.md                         # RAG 文档解析、切块、向量化、检索和引用设计
│   ├── workflow_design.md                    # 会议、维修、质量、采购、周报流程设计
│   ├── agent_design.md                       # Agent 状态、节点、边、SOP、补槽、Trace 和工具调用设计
│   ├── demo_script.md                        # 本地演示流程脚本
│   └── roadmap.md                            # 后续增强方向和生产化边界

├── scripts/                                  # 项目辅助脚本
│   ├── seed_demo_data.py                     # 导入 data/seed/*.json 到数据库
│   └── ingest_demo_docs.py                   # 批量导入 data/demo_docs 文档，解析、切块、向量化、入库

├── .env.example                              # 环境变量模板，不包含真实密钥
├── .gitignore                                # Git 忽略规则
├── docker-compose.yml                        # 一键启动 PostgreSQL/pgvector、backend、frontend
├── README.md                                 # GitHub 首页说明
├── SUPERVISOR_COMPATIBILITY.md               # 面向业务负责人和管理层的项目说明
└── LICENSE                                   # 权利保留声明

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

当前版本使用请求头模拟角色：

```text
X-User-Role: manager
```

规则：

- 普通员工可以查询知识库、上传文档、生成流程草稿。
- 主管或管理员可以查看审批、批准审批、拒绝审批、查看审计日志、申请删除文档。
- 高风险动作先进入 approvals 表。
- 审批通过后才写入正式业务表。

当前版本不直接接入真实 ERP、MES、OA、飞书、钉钉或企业微信，不处理真实企业敏感文件，不替代质量、安全、财务等责任岗位的最终判断。

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

- 当前权限是本地角色模拟，不是生产级统一认证。
- 当前文件存储使用本地 uploads 目录，不是生产级对象存储。
- 当前本地演示向量用于无 API Key 场景，正式知识库应配置真实 Embedding 服务。
- 当前工作流为固定流程，不是让 Agent 自由执行所有企业动作。
- 当前只开放设备维修和质量异常两类工单的新建流程。

## License

Copyright (c) 2026 xhlnga. All rights reserved.

本项目源代码仅用于公开展示、技术评估和学习参考。未经作者书面许可，任何个人或组织不得复制、修改、分发、商用、部署，或基于本项目创建衍生作品。

如需使用、部署、二次开发、商业合作或在企业内部试点，请先联系作者取得授权。
