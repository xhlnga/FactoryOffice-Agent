# 企业部署说明

本文档说明如何把 FactoryOffice-Agent 从本地演示模式部署成企业内网 PoC。

## 部署目标

企业部署至少包含：

- PostgreSQL + pgvector：业务数据、审批、审计和向量数据
- Redis：后台任务队列和失败重试
- Backend：FastAPI 服务
- Worker：通知、组织同步、外部业务同步、SLA 的后台任务
- Scheduler：周期扫描失败任务和 SLA 状态
- Frontend：Vue 前端

## 推荐步骤

1. 复制环境变量模板：

```bash
cp .env.example.enterprise .env
```

2. 修改 `.env`：

```text
APP_ENV=production
FRONTEND_BASE_URL=https://your-domain.example.com
DATABASE_URL=postgresql+psycopg://factory_user:factory_pass@postgres:5432/factory_agent
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=["https://your-domain.example.com"]
AUTH_SECRET_KEY=替换成随机长字符串
ENCRYPTION_KEY=替换成企业密钥
```

3. 启动企业版 compose：

```bash
docker compose -f docker-compose.enterprise.yml up -d --build
```

4. 检查服务：

```bash
docker compose -f docker-compose.enterprise.yml ps
```

## 企业集成配置

后台支持两种配置来源：

- `.env`：部署级密钥和默认参数
- 数据库 `integration_configs`：企业微信、钉钉、飞书、OA/ERP/MES/WMS 的启用状态、Webhook、回调地址和密钥引用

生产环境不要把真实密钥写入 Git。推荐把密钥放在企业密钥系统或 Docker secret，再在 `encrypted_config` 中保存密钥引用。

## 后台任务

企业版默认启动：

- `worker`：执行异步任务和失败重试
- `scheduler`：周期扫描通知、组织同步、SLA、外部同步和清理任务

后台任务失败不会阻断主业务流程。失败原因会落到通知投递、外部 ID 映射或集成事件中，方便排查。

## 生产注意事项

- 必须关闭默认 `*` CORS。
- 必须替换 `AUTH_SECRET_KEY` 和 `ENCRYPTION_KEY`。
- 上传目录需要定期备份。
- PostgreSQL 和 Redis 不建议直接暴露公网。
- 企业微信、钉钉、飞书回调地址必须使用 HTTPS。
- 真正接 ERP/MES/WMS 时，需要按企业字段做映射，不能假设所有厂商字段一致。

