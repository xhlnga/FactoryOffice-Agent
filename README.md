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

```text

FactoryOffice-Agent/
├── 00_project_truth/                         # 项目事实中心
│   └── PROJECT_SSOT.md                       # 项目唯一真源，定义项目名称、定位、范围、边界、技术栈、工作流和不做什么
│
├── backend/                                  # FastAPI 后端服务
│   ├── app/                                  # 后端主应用代码
│   │   ├── __init__.py                       # Python 包标识
│   │   ├── main.py                           # FastAPI 入口，创建 app、挂载路由、配置 CORS、注册异常处理
│   │   │
│   │   ├── api/                              # HTTP API 路由层
│   │   │   ├── __init__.py                   # API 包标识
│   │   │   └── v1/                           # API v1 版本目录
│   │   │       ├── __init__.py               # v1 包标识
│   │   │       ├── router.py                 # API v1 总路由，统一注册所有 endpoints
│   │   │       └── endpoints/                # 具体业务接口
│   │   │           ├── __init__.py           # endpoints 包标识
│   │   │           ├── health.py             # 健康检查接口，验证后端服务是否可用
│   │   │           ├── auth.py               # 本地用户身份模拟和角色验证入口
│   │   │           ├── documents.py          # 文档上传、文档列表、文档详情、文档删除申请
│   │   │           ├── knowledge.py          # 知识库检索和知识库问答接口
│   │   │           ├── agent.py              # 通用 Agent 对话入口，识别意图并分发到知识库或业务流程
│   │   │           ├── workflows.py          # 固定办公流程接口：会议、维修、质量、采购、周报
│   │   │           ├── tasks.py              # 任务列表、任务详情、任务创建接口
│   │   │           ├── tickets.py            # 工单列表、工单详情、工单创建接口
│   │   │           ├── purchases.py          # 采购申请列表、详情、创建接口
│   │   │           ├── approvals.py          # 审批列表、审批详情、批准、拒绝接口
│   │   │           └── audit_logs.py         # 审计日志列表和详情查询接口
│   │   │
│   │   ├── core/                             # 后端基础设施层
│   │   │   ├── __init__.py                   # core 包标识
│   │   │   ├── config.py                     # 读取环境变量，管理数据库、上传目录、模型、CORS 等配置
│   │   │   ├── database.py                   # SQLAlchemy Engine、Session、数据库依赖注入
│   │   │   ├── security.py                   # 角色权限判断，定义员工、主管、管理员的接口访问边界
│   │   │   ├── logging.py                    # 后端日志格式和日志级别配置
│   │   │   └── exceptions.py                 # 统一异常类型和 FastAPI 异常处理
│   │   │
│   │   ├── models/                           # SQLAlchemy 数据库模型
│   │   │   ├── __init__.py                   # 模型统一导入
│   │   │   ├── base.py                       # SQLAlchemy Declarative Base 和通用时间字段
│   │   │   ├── user.py                       # users 用户表模型
│   │   │   ├── document.py                   # documents 文档表模型，记录上传文档和软删除状态
│   │   │   ├── document_chunk.py             # document_chunks 文档切块和向量字段模型
│   │   │   ├── task.py                       # tasks 任务表模型
│   │   │   ├── ticket.py                     # tickets 工单表模型，覆盖设备维修和质量异常
│   │   │   ├── purchase_request.py           # purchase_requests 采购申请表模型
│   │   │   ├── approval.py                   # approvals 审批表模型，记录待确认动作和审批结果
│   │   │   └── audit_log.py                  # audit_logs 审计日志表模型
│   │   │
│   │   ├── schemas/                          # Pydantic 请求和响应结构
│   │   │   ├── __init__.py                   # schemas 包标识
│   │   │   ├── common.py                     # 通用响应、分页、状态结构
│   │   │   ├── user.py                       # 用户响应结构
│   │   │   ├── document.py                   # 文档上传、文档详情、文档切块响应结构
│   │   │   ├── knowledge.py                  # 知识库检索、问答、引用来源结构
│   │   │   ├── agent.py                      # Agent 对话请求、响应、工具调用展示结构
│   │   │   ├── workflow.py                   # 会议、维修、质量、采购、周报工作流结构
│   │   │   ├── task.py                       # 任务创建、任务读取结构
│   │   │   ├── ticket.py                     # 工单创建、工单读取结构
│   │   │   ├── purchase_request.py           # 采购申请创建、读取结构
│   │   │   ├── approval.py                   # 审批创建、审批读取、批准/拒绝结构
│   │   │   └── audit_log.py                  # 审计日志读取结构
│   │   │
│   │   ├── services/                         # 业务服务层
│   │   │   ├── __init__.py                   # services 包标识
│   │   │   ├── document_service.py           # 文档保存、解析、切块、入库、软删除申请
│   │   │   ├── knowledge_service.py          # 串联 RAG 检索、Prompt 构造、LLM 回答和引用来源
│   │   │   ├── task_service.py               # 任务创建、查询、列表分页
│   │   │   ├── ticket_service.py             # 设备维修工单和质量异常工单创建、查询
│   │   │   ├── purchase_service.py           # 采购申请创建、字段校验、查询
│   │   │   ├── approval_service.py           # 创建审批、批准审批、拒绝审批、审批后执行业务动作
│   │   │   ├── approval_guard.py             # 高风险动作判断规则，决定是否必须进入人工审批
│   │   │   ├── audit_service.py              # 写入和查询审计日志
│   │   │   └── llm_service.py                # OpenAI-compatible LLM 调用封装和本地兜底回答
│   │   │
│   │   ├── rag/                              # RAG 知识库模块
│   │   │   ├── __init__.py                   # rag 包标识
│   │   │   ├── document_loader.py            # PDF、DOCX、TXT、Markdown 文档解析为纯文本
│   │   │   ├── text_splitter.py              # 文档切块和重叠处理
│   │   │   ├── embedding_client.py           # Embedding 客户端，支持真实 API 和本地演示向量
│   │   │   ├── vector_store.py               # pgvector 存储、向量检索、chunk 返回
│   │   │   ├── retriever.py                  # 根据用户问题检索相关文档片段
│   │   │   ├── reranker.py                   # 检索结果重排和业务领域过滤
│   │   │   └── prompt_builder.py             # 构造带引用来源的 RAG 回答 Prompt
│   │   │
│   │   ├── agents/                           # Agent 编排模块
│   │   │   ├── __init__.py                   # agents 包标识
│   │   │   ├── factory_office_agent.py       # Agent 总入口，优先使用 LangGraph，缺失时走本地降级流程
│   │   │   ├── graph_state.py                # Agent 状态定义，包括用户输入、意图、检索结果、工具调用等
│   │   │   ├── graph_nodes.py                # 意图识别、知识检索、流程草稿生成、审批判断等节点
│   │   │   ├── graph_edges.py                # 根据意图和状态决定下一步流转
│   │   │   └── prompts.py                    # 制造业 Agent 系统提示词和任务提示词
│   │   │
│   │   ├── workflows/                        # 固定办公流程模块
│   │   │   ├── __init__.py                   # workflows 包标识
│   │   │   ├── meeting_to_tasks.py           # 会议纪要转任务草稿
│   │   │   ├── maintenance_ticket.py         # 设备异常转维修工单草稿
│   │   │   ├── quality_issue.py              # 质量异常转 NCR/质量异常工单草稿
│   │   │   ├── purchase_request.py           # 采购需求转采购申请草稿，并提示缺失字段
│   │   │   └── weekly_report.py              # 项目记录转周报草稿
│   │   │
│   │   ├── tools/                            # Agent 可调用工具层
│   │   │   ├── __init__.py                   # tools 包标识
│   │   │   ├── base.py                       # 工具统一结构，定义工具名称、参数、结果格式
│   │   │   ├── knowledge_tools.py            # 知识库搜索工具
│   │   │   ├── task_tools.py                 # 创建任务、查询任务工具
│   │   │   ├── ticket_tools.py               # 创建维修/质量工单、查询工单工具
│   │   │   ├── purchase_tools.py             # 创建采购申请、查询采购申请工具
│   │   │   ├── approval_tools.py             # 创建审批记录、审批状态处理工具
│   │   │   └── notification_tools.py         # 通知/邮件草稿生成工具，当前不真实发送
│   │   │
│   │   ├── evaluators/                       # RAG 和工作流评测模块
│   │   │   ├── rag_eval.py                   # 知识库问答评测，检查答案和引用来源质量
│   │   │   ├── workflow_eval.py              # 工作流输出评测，检查字段完整性和流程合理性
│   │   │   └── test_cases.py                 # 评测用例集合
│   │   │
│   │   └── utils/                            # 后端通用工具函数
│   │       ├── __init__.py                   # utils 包标识
│   │       ├── file_utils.py                 # 文件名清洗、扩展名判断、哈希计算、上传安全校验
│   │       ├── time_utils.py                 # 时间格式化、当前时间、日期处理
│   │       ├── json_utils.py                 # JSON 安全解析、序列化、字段提取
│   │       └── id_utils.py                   # 业务 ID 和追踪 ID 生成
│   │
│   ├── alembic/                              # 数据库迁移目录
│   │   ├── README                            # Alembic 目录说明
│   │   ├── env.py                            # Alembic 运行环境，加载模型和数据库配置
│   │   ├── script.py.mako                    # Alembic 迁移脚本模板
│   │   └── versions/                         # 具体迁移版本
│   │       └── 20260502_0001_initial_schema.py # 初始化数据库表、pgvector 扩展和索引
│   │
│   ├── tests/                                # 后端测试
│   │   ├── test_health.py                    # 健康检查测试
│   │   ├── test_document_upload.py           # 文档上传、解析、软删除相关测试
│   │   ├── test_rag_search.py                # 知识库检索测试
│   │   ├── test_knowledge_ask.py             # 知识库问答和引用来源测试
│   │   ├── test_workflows.py                 # 会议、维修、采购、周报工作流测试
│   │   ├── test_quality_issue_workflow.py    # 质量异常工作流测试
│   │   ├── test_approvals.py                 # 审批创建、批准、拒绝和执行动作测试
│   │   ├── test_agent_routes.py              # Agent 意图识别和路由测试
│   │   ├── test_security.py                  # 权限角色和接口访问边界测试
│   │   ├── test_seed_demo_data.py            # 种子数据导入测试
│   │   └── test_ingest_demo_docs.py          # 演示文档解析、切块、导入测试
│   │
│   ├── data/                                 # 后端运行期数据目录，主要用于容器内文件路径兼容
│   ├── requirements.txt                      # 后端运行依赖
│   ├── requirements-dev.txt                  # 后端开发和测试依赖
│   ├── Dockerfile                            # 后端 Docker 镜像构建文件
│   ├── .dockerignore                         # 后端 Docker 构建忽略规则
│   └── alembic.ini                           # Alembic 配置文件
│
├── frontend/                                 # Vue3 + Element Plus 前端
│   ├── src/                                  # 前端源码
│   │   ├── main.ts                           # Vue 应用入口，挂载 App、路由和 Element Plus
│   │   ├── App.vue                           # 根组件，定义整体布局入口
│   │   ├── env.d.ts                          # TypeScript 环境类型声明
│   │   │
│   │   ├── router/                           # 前端路由
│   │   │   └── index.ts                      # 页面路由配置
│   │   │
│   │   ├── api/                              # 前端接口请求封装
│   │   │   ├── http.ts                       # Axios 实例、baseURL、错误处理
│   │   │   ├── documents.ts                  # 文档上传、列表、切块、删除申请接口
│   │   │   ├── knowledge.ts                  # 知识库搜索和问答接口
│   │   │   ├── agent.ts                      # 通用 Agent 对话接口
│   │   │   ├── workflows.ts                  # 会议、维修、质量、采购、周报工作流接口
│   │   │   ├── tasks.ts                      # 任务列表、详情、创建接口
│   │   │   ├── tickets.ts                    # 工单列表、详情、创建接口
│   │   │   ├── purchases.ts                  # 采购申请列表、详情、创建接口
│   │   │   ├── approvals.ts                  # 审批列表、批准、拒绝接口
│   │   │   └── auditLogs.ts                  # 审计日志列表和详情接口
│   │   │
│   │   └── views/                            # 前端页面
│   │       ├── DashboardView.vue             # 首页仪表盘，展示文档、任务、工单、审批、日志概览
│   │       ├── KnowledgeBaseView.vue         # 知识库页面，支持文档上传、文档列表、知识库问答、引用来源展示
│   │       ├── AgentChatView.vue             # AI 助手页面，统一入口处理知识问答和业务流程意图
│   │       ├── WorkflowsView.vue             # 办公流程页面，提供会议、维修、质量、采购、周报输入区
│   │       ├── TasksView.vue                 # 任务页面，展示任务列表和任务详情
│   │       ├── TicketsView.vue               # 工单页面，展示设备维修和质量异常工单
│   │       ├── PurchasesView.vue             # 采购申请页面，展示采购申请状态和详情
│   │       ├── ApprovalsView.vue             # 审批页面，支持批准和拒绝待执行动作
│   │       └── AuditLogsView.vue             # 审计日志页面，展示工具调用参数和执行结果
│   │
│   ├── public/                               # 前端静态资源目录
│   │   └── .gitkeep                          # 保留空目录
│   │
│   ├── index.html                            # Vite HTML 入口
│   ├── package.json                          # 前端依赖和 npm 脚本
│   ├── package-lock.json                     # 前端依赖锁定文件，保证安装版本一致
│   ├── vite.config.ts                        # Vite 配置、开发服务器端口和代理
│   ├── tsconfig.json                         # TypeScript 配置
│   ├── Dockerfile                            # 前端 Docker 镜像构建文件
│   └── .dockerignore                         # 前端 Docker 构建忽略规则
│
├── data/                                     # 演示数据与上传目录
│   ├── demo_docs/                            # 制造业模拟知识库文档
│   │   ├── .gitkeep                          # 保留目录
│   │   ├── 采购管理制度.md                   # 采购流程、金额阈值、审批规则演示文档
│   │   ├── 差旅报销制度.md                   # 差旅申请、费用标准、票据和报销审批演示文档
│   │   ├── 设备维修手册_空压机.md            # 空压机报警、排查、维修建议演示文档
│   │   ├── 质量异常处理流程.md               # 质量异常、隔离、复检、NCR 流程演示文档
│   │   ├── 安全生产规范.md                   # 安全作业、风险审批、现场规范演示文档
│   │   └── 项目周报模板.md                   # 周报结构、风险项、下周计划演示模板
│   │
│   ├── seed/                                 # 初始化业务数据
│   │   ├── users.json                        # 演示用户、角色、部门数据
│   │   ├── tasks.json                        # 演示任务数据
│   │   ├── tickets.json                      # 演示设备维修和质量异常工单数据
│   │   ├── purchase_requests.json            # 演示采购申请数据
│   │   ├── approvals.json                    # 演示待审批和已审批记录
│   │   └── audit_logs.json                   # 演示审计日志记录
│   │
│   └── uploads/                              # 本地上传文件目录
│       └── .gitkeep                          # 保留上传目录，不提交真实上传文件
│
├── docs/                                     # 普通项目文档
│   ├── architecture.md                       # 系统架构、模块关系和部署结构说明
│   ├── api.md                                # 后端 API 说明
│   ├── database.md                           # 数据库表设计和实体关系说明
│   ├── rag_design.md                         # RAG 文档解析、切块、向量化、检索和引用设计
│   ├── workflow_design.md                    # 办公流程设计，说明会议、维修、质量、采购、周报流程
│   ├── agent_design.md                       # Agent 状态、节点、边、意图识别和工具调用说明
│   ├── demo_script.md                        # 本地演示流程脚本
│   └── roadmap.md                            # 后续规划和生产化增强方向
│
├── scripts/                                  # 项目辅助脚本
│   ├── seed_demo_data.py                     # 导入 data/seed/*.json 到数据库
│   └── ingest_demo_docs.py                   # 批量导入 data/demo_docs 文档，解析、切块、向量化、入库
│
├── .env.example                              # 环境变量模板，不包含真实密钥
├── .gitignore                                # Git 忽略规则，排除 env、缓存、上传文件、依赖目录等
├── docker-compose.yml                        # 一键启动 PostgreSQL/pgvector、后端、前端
├── README.md                                 # GitHub 首页说明，介绍项目价值、功能、启动方式、结构和边界
├── SUPERVISOR_COMPATIBILITY.md               # 面向业务负责人和管理层的说明，解释项目价值、适用范围和风险边界
└── LICENSE                                   # 权利保留声明，未经作者书面许可不得复制、修改、分发、商用或部署


```
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
