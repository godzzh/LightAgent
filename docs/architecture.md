# 架构设计

## 1. 总体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        浏览器 / 第三方系统                     │
│   Vue 3 SPA（管理后台）            外部 API（Bearer API Key）   │
└───────────────┬─────────────────────────────┬───────────────┘
                │ HTTPS / SSE                 │ /api/v1/open/*
┌───────────────▼─────────────────────────────▼───────────────┐
│                      Nginx（静态资源 + 反向代理）               │
│         SSE 关闭缓冲：proxy_buffering off / 600s 超时          │
└───────────────┬─────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────┐
│                        FastAPI 应用层                         │
│  api/v1/*  统一响应信封（EnvelopeRoute）/ JWT 鉴权 / SSE 输出   │
├─────────────────────────────────────────────────────────────┤
│                        服务层 services                        │
│  agent(装配+会话+日志)  workflow(执行+落库)  knowledge(入库+检索) │
│  tools(工具解析)        workspace                            │
├─────────────────────────────────────────────────────────────┤
│                        引擎层 engines                         │
│  agent_runtime  workflow_engine  nodes  variable_resolver      │
│  safe_eval（受限表达式）                                        │
├─────────────────────────────────────────────────────────────┤
│    Provider 抽象层            Tool Registry                   │
│  deepseek / openai_compat     builtin / custom(http)          │
├─────────────────────────────────────────────────────────────┤
│  数据层：SQLAlchemy 2.x(async)  Alembic   FileStorage          │
│  PostgreSQL + pgvector（生产）  /  SQLite（本地）  Redis（预留） │
└─────────────────────────────────────────────────────────────┘
```

### 分层约束

| 层 | 允许依赖 | 禁止 |
| --- | --- | --- |
| api | services、schemas、core | 直接写业务逻辑、直接拼 SQL |
| services | engines、models、providers | 直接返回 ORM 对象给路由（统一转 dict） |
| engines | providers、tool_registry、core | 访问 HTTP 请求上下文、写数据库 |
| providers | 厂商 SDK | 被业务层直接引用 |
| models | core.database | 依赖上层任何模块 |

关键点：**引擎不碰数据库**，只做纯执行并通过事件流（dict）向上汇报；持久化由 services 完成。这让引擎可被单元测试直接驱动（见 `tests/test_agent_runtime.py`）。

## 2. Agent 执行流程

```
用户问题
  │
  ├─ 1. 加载应用配置 → 解析模型配置 → 构造 Provider
  ├─ 2. 装配工具（内置 registry / DB 自定义 HTTP 工具）
  ├─ 3. 知识检索（可选）：question → embedding → TopK → 阈值过滤
  ├─ 4. 渲染 Prompt：{{query}} / {{knowledge_context}} / 自定义变量
  ├─ 5. 进入循环（最多 max_steps）
  │      ├─ provider.chat_stream(tools=schemas)
  │      ├─ 有 tool_calls → 参数校验 → 执行（带超时）→ 结果回填 messages → 继续
  │      └─ 无 tool_calls → 结束，输出最终答案
  └─ 6. 事件流：run_started / knowledge / context / token / tool_call /
               tool_result / step / run_completed | run_error
```

资源约束（全部在 `AgentRuntimeConfig` 中可配）：`max_steps`、`max_tool_calls`、`tool_timeout`、`total_timeout`（`asyncio.timeout`）、`max_context_messages`。

安全：知识片段与工具输出在系统提示中被显式降级为「参考资料」，任何其中的指令不得提升为系统指令（Prompt Injection 防护）。

## 3. 工作流执行流程

```
graph JSON {nodes[], edges[]}
  → validate：存在 start、存在 answer/end、无环、连线端点合法、节点类型已知
  → topo_order：Kahn 拓扑排序（start 优先）
  → 逐节点执行：
       active?  ← 所有入边来源已执行，且条件节点的 sourceHandle 与分支匹配
       emit node_started → execute → emit node_completed / node_failed
  → 变量上下文：{ node_id: outputs }，`{{llm_1.text}}` 由 deep_render 解析
  → 结束：Answer 节点汇总 ctx.answer → run_completed
```

节点统一接口：`validate_config / validate_input / execute / validate_output`（实现为 `NODE_EXECUTORS[type](node, ctx)`，校验内嵌于各节点）。

## 4. SSE 事件协议

| 事件 | 方向 | 说明 |
| --- | --- | --- |
| `run_started` | 服务端 | run_id / session_id / app_id |
| `knowledge` | 服务端 | 召回片段（含分数与来源） |
| `context` | 服务端 | 上下文摘要（仅角色与长度，不泄露完整提示词） |
| `token` | 服务端 | 增量文本 |
| `tool_call` / `tool_result` | 服务端 | 工具名、入参、结果、耗时、错误 |
| `node_started` / `node_completed` / `node_failed` / `node_skipped` | 服务端 | 工作流节点状态 |
| `run_completed` | 服务端 | 最终输出 + usage |
| `run_error` / `run_failed` | 服务端 | 错误信息（带类型） |
| `stream_closed` | 服务端 | 流正常/异常结束标记 |

客户端断开 → Starlette 取消生成器 → `asyncio.CancelledError` 向上传播 → Provider 请求取消 → 服务层 `finally` 落库。Nginx 层已关闭缓冲避免粘包。

## 5. 数据库选型与降级策略

| 能力 | 生产（PostgreSQL） | 本地（SQLite） |
| --- | --- | --- |
| 表结构 | Alembic 迁移 | 启动 `create_all` + 迁移脚本可用 |
| JSON 字段 | JSONB 语义（`sa.JSON`） | JSON 文本 |
| 向量 | pgvector 扩展已创建 | 应用层余弦计算 |
| 后台任务 | worker 容器轮询 | 进程内 `asyncio.create_task` |

统一通过 `settings.DATABASE_URL` 切换，业务代码零分叉。

## 6. 安全设计

1. API Key / 模型密钥：Fernet（密钥由 SECRET_KEY 派生）加密入库，读取时解密，对外只给脱敏串。
2. 对外 API Key：`la-` + `token_urlsafe(32)`，库中仅存 SHA256 与 12 位前缀。
3. 密码：PBKDF2-HMAC-SHA256（260k 迭代，随机盐）。
4. HTTP 工具 / HTTP 节点：`validate_public_url` 阻断内网、保留地址、云元数据（169.254.169.254）、非 http(s) 协议，并做 DNS 解析后二次校验。
5. Code 节点：AST 白名单解释器，禁止属性访问、import、eval/exec。
6. 上传：后缀白名单 + 大小限制 + 随机存储名（不使用原始文件名落盘）。
7. 日志：loguru patcher 对含 api_key/password/token 的消息做截断脱敏；日志不落完整 Prompt。
8. SQL 注入：全部走 SQLAlchemy 参数化 / ORM 表达式。
