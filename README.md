# EchoMind

EchoMind 客服 Agent 项目的 Python 后端、Vue 前端和 Java 后端集中在此仓库。

```text
EchoMind/          Python 后端、测试及 wiki 文档
EchoMindFrontend/  Vue 前端和全栈 Docker Compose
EchoMindJava/      Java 后端
```

## Docker 启动

1. 将 `EchoMindFrontend/.env.example` 复制为 `EchoMindFrontend/.env`。
2. 在 `.env` 中填写所用模型服务的 API Key、兼容接口地址、模型 ID，并设置 Redis 密码。不要提交真实 `.env`。
3. 在 `EchoMindFrontend` 目录运行 `docker compose up -d --build`。

前端默认可通过 `http://localhost` 访问。更详细的架构和使用说明见 `EchoMind/wiki/`；各模块也有自己的 README。

此仓库不包含运行数据库、缓存、构建产物或 API Key。
