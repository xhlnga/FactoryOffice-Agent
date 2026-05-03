# Agent 设计

本文档说明 FactoryOffice-Agent 的 Agent 编排思路。项目事实以 [`../00_project_truth/PROJECT_SSOT.md`](../00_project_truth/PROJECT_SSOT.md) 为准。

## 1. Agent 定位

本项目中的 Agent 不是自由聊天机器人，而是企业办公流程调度器。

它需要完成：

- 判断用户输入属于哪类任务。
- 判断是否需要查知识库。
- 判断是否需要生成业务草稿。
- 判断是否需要调用工具。
- 判断是否需要人工审批。
- 输出可追踪的处理结果。

## 2. 模块划分

代码位于 `backend/app/agents/`。

| 文件 | 作用 |
| --- | --- |
| `factory_office_agent.py` | Agent 总入口 |
| `graph_state.py` | Agent 状态定义 |
| `graph_nodes.py` | 意图识别、检索、工具选择、审批判断等节点 |
| `graph_edges.py` | 图流转逻辑 |
| `prompts.py` | Agent 提示词 |
| `task_state.py` | 企业任务状态机定义 |
| `sop_registry.py` | 根据意图匹配 SOP |
| `slot_filling.py` | 检查必填字段、支持多轮补槽 |
| `trace.py` | 生成 Agent 可解释执行轨迹 |

SOP 定义位于 `backend/app/workflows/sop_definitions.py`，用于声明每类企业流程需要哪些字段、是否需要审批、对应哪个工具和业务表。

## 3. 状态设计

Agent 状态应包含：

- 用户输入
- 多轮上下文
- 用户 ID
- 识别出的意图
- 命中的 SOP
- 当前任务状态
- 已识别字段
- 缺失字段
- 下一步追问
- 检索结果
- 草稿结果
- 工具调用候选
- 是否需要审批
- Agent Trace
- 最终回答
- 错误信息

示例：

```json
{
  "message": "A3 产线空压机 E07 报警，产线暂停。",
  "user_id": 3,
  "intent": "maintenance_ticket",
  "sop_id": "maintenance_ticket",
  "sop_name": "设备维修工单 SOP",
  "task_status": "waiting_approval",
  "slot_values": {
    "equipment_or_line": "A3 产线",
    "abnormal_signal": "E07 报警"
  },
  "missing_fields": [],
  "retrieved_chunks": [],
  "tool_calls": [
    {
      "tool_name": "preview_maintenance_ticket",
      "requires_approval": true
    }
  ],
  "requires_approval": true,
  "trace_steps": [
    {
      "step": "match_sop",
      "status": "matched"
    },
    {
      "step": "slot_filling",
      "status": "complete"
    }
  ],
  "answer": "已生成维修工单草稿，提交前需要人工确认。"
}
```

## 4. 任务状态机

当前 Agent 任务状态包括：

| 状态 | 含义 |
| --- | --- |
| `new` | 新任务或尚未匹配到明确 SOP |
| `collecting_info` | 已识别 SOP，但缺少必填字段，需要追问 |
| `waiting_approval` | 草稿已生成，正式写入前等待人工审批 |
| `approved` | 已审批通过，等待执行或已进入执行阶段 |
| `executing` | 正在执行工具或写入业务表 |
| `completed` | 当前动作已完成或仅生成无风险草稿 |
| `failed` | 流程执行失败 |
| `cancelled` | 用户或审批人取消 |
| `suspended` | 因外部依赖、权限或业务原因暂停 |

## 5. SOP 配置

当前内置 SOP：

| SOP | 必填字段 | 审批策略 |
| --- | --- | --- |
| 知识库问答 SOP | 问题 | 不需要审批 |
| 会议纪要转任务 SOP | 会议纪要正文、任务事项 | 字段完整后审批 |
| 设备维修工单 SOP | 设备或产线、异常现象、异常描述 | 字段完整后审批 |
| 质量异常处理 SOP | 异常现象或检验结果、影响范围、异常描述 | 字段完整后审批 |
| 采购申请 SOP | 物品名称、数量、采购原因、预算、供应商 | 字段完整后审批 |
| 项目周报生成 SOP | 项目记录 | 不需要审批 |

SOP 的作用是把“写死流程”提升为“可声明、可追踪、可扩展的企业流程定义”。后续如果企业要增加安全巡检、差旅申请、客户投诉等流程，可以新增 SOP 定义和对应工作流。

## 6. 多轮补槽

当用户输入不完整时，Agent 不直接失败，而是进入 `collecting_info` 状态并返回缺失字段。

示例：

```text
用户：帮我申请采购 20 个温度传感器，用于产线改造。
Agent：缺少预算、供应商，请补充。
用户：预算 48000 元，供应商为华南传感器。
Agent：字段已补齐，生成采购申请草稿并进入 waiting_approval。
```

当前版本通过 `context` 参数承接上一轮任务信息，后续可进一步持久化到 `agent_sessions` 或 `agent_tasks` 表。

## 7. Agent Trace

Agent 每次执行都会返回结构化 Trace：

```text
classify_intent
match_sop
slot_filling
select_tools
approval_gate
final_answer
```

Trace 用于说明系统为什么命中某个 SOP、缺哪些字段、是否需要审批、下一步状态是什么。它面向企业调试和审计，而不是展示模型推理链。

## 8. 意图类型

推荐意图：

| 意图 | 说明 |
| --- | --- |
| `knowledge_qa` | 企业知识库问答 |
| `meeting_to_tasks` | 会议纪要转任务 |
| `maintenance_ticket` | 设备异常转维修工单 |
| `quality_issue` | 质量异常处理 |
| `purchase_request` | 采购需求转申请草稿 |
| `weekly_report` | 项目周报生成 |
| `unknown` | 无法判断 |

## 9. 图流转

```text
接收用户输入
  ↓
意图识别
  ↓
匹配 SOP
  ↓
检查槽位是否完整
  ↓
是否需要知识库检索
  ↓
执行固定工作流或工具预览
  ↓
判断是否需要审批
  ↓
生成最终回答
```

## 10. 工具调用

工具位于 `backend/app/tools/`。

常见工具：

- 搜索知识库
- 生成任务草稿
- 创建任务
- 生成维修工单草稿
- 创建维修工单
- 生成采购申请草稿
- 创建采购申请
- 创建审批记录
- 写审计日志

工具返回需要包含：

- 工具名
- 是否成功
- 业务消息
- 结构化数据
- 是否需要审批
- 待审批动作类型
- 待审批参数

## 11. 审批判断

Agent 不应该直接执行高风险动作。

需要审批的场景：

- 写入任务、工单、采购申请等业务表
- 删除知识库文档
- 批量操作
- 涉及安全、质量、客户交付或预算风险
- 用户表达中存在“先凑合用”“绕过保护”“不走审批”等风险信号

不需要审批的场景：

- 查询制度
- 生成草稿
- 查询已有记录
- 汇总公开演示数据

## 12. 与 LangGraph 的关系

LangGraph 用于表达有状态、有分支、可暂停、可恢复的流程。

本项目保留降级执行能力：

- 环境中有 LangGraph 时，可编译图并执行节点流转。
- 环境中暂未安装 LangGraph 时，可用普通函数完成基础流程。

这样可以保证本地开发、测试和演示更稳定。

## 13. Agent 输出要求

Agent 回答应满足：

- 用中文表达业务含义。
- 明确是否查了知识库。
- 明确命中了哪个 SOP。
- 明确当前任务状态。
- 明确缺失字段和下一步追问。
- 明确是否生成草稿。
- 明确是否需要人工确认。
- 返回结构化 Trace，便于调试和审计。
- 涉及安全和质量风险时不鼓励冒险操作。
- 不编造文档中没有的金额、审批人、客户反馈或测试结果。

## 14. 现实边界

Agent 的价值是辅助流程，不是替代企业责任人。

它可以帮助员工更快完成：

- 查制度
- 补字段
- 写草稿
- 识别风险
- 触发审批
- 留存日志

但现场判断、最终审批和责任承担仍由企业人员完成。
