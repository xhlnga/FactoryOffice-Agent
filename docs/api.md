# API 说明

本文档描述后端 API 的业务用途和接口边界。项目事实以 [`../00_project_truth/PROJECT_SSOT.md`](../00_project_truth/PROJECT_SSOT.md) 为准。

默认后端地址：

```text
http://localhost:8000
```

统一 API 前缀：

```text
/api
```

交互式接口文档：

```text
http://localhost:8000/docs
```

## 1. 健康检查

### GET `/api/health`

用于确认后端服务是否启动。

响应示例：

```json
{
  "status": "ok"
}
```

## 2. 本地演示登录与权限

当前阶段使用本地演示登录，后续可替换为企业 SSO、企业微信、钉钉或飞书登录。
涉及审批、审计日志和文档删除申请的接口优先读取登录返回的 Bearer token：

```text
Authorization: Bearer <access_token>
```

为了方便本地调试，也兼容请求头角色：

```text
X-User-Role: manager
```

未提供该请求头时，系统按普通员工处理，只允许执行知识库查询、文档上传和流程草稿生成等低风险操作。

### POST `/api/auth/login`

请求示例：

```json
{
  "username": "li_qiang",
  "role": "employee",
  "department": "设备部"
}
```

响应包含本地演示 token 和用户信息。

### GET `/api/auth/me`

返回当前请求身份。携带 Bearer token 时返回 token 中的用户和角色；未登录时返回本地演示默认身份。

## 3. 文档管理

### GET `/api/documents`

查询未删除的知识库文档。

### POST `/api/documents/upload`

上传企业文档并创建文档记录。

参数：

- `file`：上传文件
- `category`：文档分类，默认“未分类”

说明：

- 当前接口负责保存文件、创建文档记录，并同步完成解析、切块和知识库入库。
- 如果知识库入库失败，系统会回滚文档记录并清理已保存文件，避免出现“有文档但不可检索”的半成品状态。
- 上传文件会保存到本地 uploads 目录。

### DELETE `/api/documents/{document_id}`

删除文档属于高风险动作。接口不会直接硬删除，而是创建待审批记录。
该接口需要主管或管理员角色。

响应包含：

- `document_id`
- `approval_id`
- `status`

## 4. 知识库

### POST `/api/knowledge/search`

根据用户问题检索相关文档片段。

请求示例：

```json
{
  "query": "空压机 E07 报警怎么处理？",
  "top_k": 5
}
```

说明：

- 当前接口为知识库检索入口，会返回匹配的文档切块、来源和相似度得分。
- 如果未配置真实 embedding 服务，系统使用本地确定性向量作为开发演示兜底；正式环境应配置 OpenAI-compatible embedding 服务。

### POST `/api/knowledge/ask`

基于知识库检索结果生成回答。

请求示例：

```json
{
  "question": "采购金额超过 5 万需要谁审批？",
  "top_k": 5
}
```

响应应包含：

- 用户问题
- 回答内容
- 引用来源
- 处理说明

## 5. 通用 Agent

### POST `/api/agent/chat`

Agent 总入口，用于执行意图识别、知识检索、工具选择和审批判断。

请求示例：

```json
{
  "message": "帮我申请采购20个温度传感器，用于产线设备改造。",
  "user_id": 3,
  "context": {}
}
```

多轮补槽时，前端或外部系统可以把上一轮任务上下文放入 `context`：

```json
{
  "message": "预算48000元，供应商为华南传感器。",
  "context": {
    "task_status": "collecting_info",
    "active_intent": "purchase_request",
    "active_message": "帮我申请采购20个温度传感器，用于产线设备改造。"
  }
}
```

响应包含：

- `intent`：识别出的任务类型
- `sop_id`：命中的 SOP ID
- `sop_name`：命中的 SOP 名称
- `task_status`：当前任务状态，例如 `collecting_info`、`waiting_approval`
- `slot_values`：当前已识别出的业务字段
- `missing_fields`：缺失字段和追问提示
- `next_question`：下一步需要用户补充的问题
- `answer`：回答或处理建议
- `tool_calls`：工具调用预览
- `requires_approval`：是否需要人工确认
- `trace`：Agent 执行轨迹，用于说明意图识别、SOP 匹配、补槽、工具选择和审批判断

## 6. 固定办公流程

固定流程用于降低自由 Agent 的不可控性。

### POST `/api/workflows/meeting-to-tasks`

会议纪要转任务草稿。

请求示例：

```json
{
  "content": "张丽 1 月 12 日前确认滤芯交期；赵磊下周更新点检表。"
}
```

### POST `/api/workflows/maintenance-ticket`

设备异常转维修工单草稿。

请求示例：

```json
{
  "content": "A3 产线空压机 E07 报警，末端压力波动，产线暂停 35 分钟。"
}
```

### POST `/api/workflows/quality-issue`

质量异常描述转 NCR/质量异常工单草稿。系统只生成待确认草稿，不直接判定最终责任、放行、返工或报废。

请求示例：

```json
{
  "content": "B2批次零件抽检发现3件尺寸超差，影响当前批次出货。"
}
```

### POST `/api/workflows/purchase-request`

采购需求转采购申请草稿。

请求示例：

```json
{
  "content": "申请采购 4 个空压机过滤器滤芯，用于 A3 产线空压机稳定性改善。"
}
```

### POST `/api/workflows/weekly-report`

项目记录转周报草稿。

请求示例：

```json
{
  "content": "本周完成 E07 报警排查，滤芯采购未关闭，下周完成更换和试运行。"
}
```

## 7. 任务、工单、采购

这些接口作为业务对象入口。正式写入时应遵守人工审批规则。

### 任务

- GET `/api/tasks`
- POST `/api/tasks`
- GET `/api/tasks/{task_id}`

### 工单

- GET `/api/tickets`
- POST `/api/tickets`
- GET `/api/tickets/{ticket_id}`

当前正式开放的工单类型：

- 设备维修
- 质量异常

安全隐患、IT 支持、售后问题等类型需要接入对应专业流程后再开放，系统不会把它们默认当作维修工单处理。

### 采购申请

- GET `/api/purchases`
- POST `/api/purchases`
- GET `/api/purchases/{purchase_id}`

## 8. 审批

审批列表、批准和拒绝操作需要主管或管理员角色。

### GET `/api/approvals`

查询审批列表，可按状态过滤。

状态：

```text
pending
approved
rejected
execution_failed
```

### GET `/api/approvals/pending`

查询待审批动作。

### POST `/api/approvals/{approval_id}/approve`

批准审批，并触发对应业务动作。

请求示例：

```json
{
  "reviewer": "陈浩",
  "comment": "已确认产线暂停，批准创建 P1 维修工单。"
}
```

### POST `/api/approvals/{approval_id}/reject`

拒绝审批，业务动作不会执行。

### 移动审批接口

企业微信、钉钉、飞书或通用 Webhook 通知中的 H5 审批链接会携带签名 token：

```text
/mobile/approvals/{approval_id}?token=<signed_token>
```

后端对应接口：

- GET `/api/mobile/approvals/{approval_id}?token=...`
- POST `/api/mobile/approvals/{approval_id}/approve?token=...`
- POST `/api/mobile/approvals/{approval_id}/reject?token=...`

没有管理员/主管登录态时，移动审批接口必须校验该 token，避免只靠审批 ID 操作。

## 9. 审计日志

审计日志包含用户输入、工具参数和执行结果，属于敏感运营记录，查询接口需要主管或管理员角色。

### GET `/api/audit-logs`

查询审计日志列表。

可选参数：

- `user_id`
- `action`
- `limit`

### GET `/api/audit-logs/{log_id}`

查询单条审计日志详情。

## 10. API 设计原则

- API 层不写复杂业务逻辑，复杂逻辑进入 services、workflows、tools。
- 高风险动作不直接执行，先创建 approvals 记录。
- 审批通过后的工具执行必须写 audit_logs。
- 对外响应尽量包含明确 message，方便前端展示。
- 业务枚举使用英文值，展示文案优先中文。
