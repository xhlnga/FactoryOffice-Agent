# 钉钉集成说明

本文档说明钉钉接入 FactoryOffice-Agent 的工程边界。

## 当前支持

- 钉钉通知 Provider
- 钉钉回调处理骨架
- 审批待办签名 H5 链接通知
- 后台通知失败重试
- 外部回调幂等处理

## 需要配置

```text
DINGTALK_APP_KEY
DINGTALK_APP_SECRET
INTEGRATION_CALLBACK_BASE_URL
```

数据库配置建议：

```text
platform=dingtalk
app_key=钉钉 AppKey
encrypted_config.app_secret_ref=企业密钥引用
webhook_url=钉钉机器人或业务消息出口
callback_url=https://your-domain.example.com/api/callbacks/dingtalk
status=active
```

## 推荐接入方式

第一阶段建议使用 H5 审批页：

```text
系统创建审批
  ↓
钉钉通知中带签名审批链接
  ↓
用户打开 FactoryOffice H5 页面
  ↓
批准/拒绝
  ↓
本系统更新审批和审计
```

第二阶段再接钉钉原生审批或交互卡片回调。

## 现实边界

不同企业的钉钉应用权限、审批模板和字段差异较大，本项目保留通用 Provider 和回调骨架，不硬编码某个企业模板。
