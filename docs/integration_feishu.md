# 飞书集成说明

本文档说明飞书接入 FactoryOffice-Agent 的工程边界。

## 当前支持

- 飞书通知 Provider
- 飞书事件回调骨架
- URL challenge 处理
- 审批待办签名 H5 链接通知
- 后台失败重试

## 需要配置

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
INTEGRATION_CALLBACK_BASE_URL
```

数据库配置建议：

```text
platform=feishu
app_key=飞书 AppId
encrypted_config.app_secret_ref=企业密钥引用
webhook_url=飞书机器人或消息出口
callback_url=https://your-domain.example.com/api/callbacks/feishu
status=active
```

## 事件处理

飞书事件应先完成 challenge，再处理业务事件：

```text
飞书事件
  ↓
校验 token / 解密
  ↓
识别 event_id
  ↓
幂等检查
  ↓
映射审批动作
  ↓
更新审批状态
```

## 现实边界

飞书租户、机器人、消息卡片和审批 API 版本会随企业配置不同而变化。本项目不假设固定模板，实际落地时应按企业飞书应用权限补字段映射。
