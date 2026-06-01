# 企业微信集成说明

本文档说明企业微信接入 FactoryOffice-Agent 的工程边界。

## 当前支持

- 企业微信通知 Provider
- 回调入口与签名校验骨架
- 审批待办签名 H5 链接通知
- 组织同步服务接口
- 后台失败重试

## 需要配置

```text
WECOM_CORP_ID
WECOM_AGENT_ID
WECOM_SECRET
INTEGRATION_CALLBACK_BASE_URL
```

同时在系统中创建 `integration_configs`：

```text
platform=wecom
corp_id=企业 CorpId
agent_id=应用 AgentId
encrypted_config.secret_ref=企业密钥引用
webhook_url=企业微信机器人或内部消息出口
callback_url=https://your-domain.example.com/api/callbacks/wecom
status=active
```

## 回调处理原则

企业微信回调通常涉及 URL、Token、EncodingAESKey 和加密消息。当前代码提供签名校验和解密扩展点，生产接入时应接入企业自己的解密实现。

处理链路：

```text
企业微信回调
  ↓
验签
  ↓
必要时解密
  ↓
转成内部 ApprovalCallbackEvent
  ↓
幂等检查
  ↓
审批状态更新
  ↓
审计日志
```

## 现实边界

本项目不内置企业微信私有通讯录权限申请，也不保存明文手机号。组织同步落库时应只保存必要字段和哈希字段。
