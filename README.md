# FactoryOffice-Agent

制造业企业知识库与办公流程智能体。

FactoryOffice-Agent 是一个面向制造业企业办公场景的 AI Agent 工程样板。项目围绕企业制度、SOP、设备手册、质量流程、安全规范和项目资料，提供知识库问答、流程草稿生成、人工审批、工具执行和审计追踪能力。

它不是一个只会回答问题的聊天机器人，而是一个把企业办公中的“查资料、写草稿、走审批、落业务表、留日志”串起来的完整工程闭环。

完整项目事实、范围和边界见：[`00_project_truth/PROJECT_SSOT.md`](00_project_truth/PROJECT_SSOT.md)

面向业务和管理人员的说明见：[`SUPERVISOR_COMPATIBILITY.md`](SUPERVISOR_COMPATIBILITY.md)

## 项目价值

制造业企业的日常办公通常不是单纯聊天，而是围绕制度、流程、设备、质量、采购、项目交付展开。

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

## 系统结构

```text

FactoryOffice-Agent/
├── 00_project_truth/
├── SUPERVISOR_COMPATIBILITY.md
├── backend/
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   ├── core/
│   │   ├── evaluators/
│   │   ├── models/
│   │   ├── rag/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tools/
│   │   ├── utils/
│   │   └── workflows/
│   ├── data/
│   │   └── uploads/
│   └── tests/
├── data/
│   ├── demo_docs/
│   ├── seed/
│   └── uploads/
├── docs/
├── frontend/
│   ├── public/
│   └── src/
│       ├── api/
│       ├── router/
│       └── views/
└── scripts/

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

本项目采用 MIT License。
