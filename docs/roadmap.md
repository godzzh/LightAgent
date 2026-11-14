# 分阶段开发计划与验收

开发原则：不一次性堆代码，每个阶段必须「可启动 / 可验证 / 有测试」。

## 第一阶段：项目基础框架 ✅ 已完成

- Vue 3 + Vite + TS + Naive UI + Tailwind + Pinia + Router
- FastAPI + SQLAlchemy 2.x + Alembic + Pydantic v2
- Docker Compose（frontend/backend/postgres/redis/worker/nginx）
- JWT 登录注册、默认工作空间、统一响应信封 + 全局异常
- 主框架布局（220px 侧栏 / 56px 顶栏 / 内容区）

**验收**：前后端可启动；`/health` 200；登录拿到 token；`/docs` 可访问。

## 第二阶段：模型管理 ✅ 已完成

- Provider 抽象 + DeepSeek / OpenAI 兼容实现
- Provider 与 ModelConfig CRUD、Key 加密与脱敏、连接测试
- SSE 流式通道（fetch + ReadableStream 解析）
- LLM 调用日志

**验收**：配置 DeepSeek Key → 测试连接成功 → Agent 对话获得真实流式输出。

## 第三阶段：Agent 核心 ✅ 已完成

- Agent CRUD、配置校验（Pydantic）、模板
- Prompt 变量识别与渲染、工具装配、知识绑定
- Agent Runtime：Function Calling + ReAct、步数/调用次数/超时限制
- 会话与消息持久化、Agent Run + Steps 日志
- 三栏调试页（配置 / 对话 / 运行详情）

**验收**：创建 Agent → 绑定「数学计算」工具 → 提问触发真实工具调用并回填结果；运行详情展示入参/出参/Token/耗时。

## 第四阶段：知识库 RAG 🟡 基本完成（依赖外部 Embedding 模型）

- 数据集 CRUD、切片策略配置、切片预览
- PDF/DOCX/TXT/MD/HTML 解析、清洗、切片
- 异步流水线（状态机 + 进度 + 失败原因）、重索引
- 切片查看/修改（改后重新向量化）
- 检索测试（向量 + 关键词加权、阈值、TopK、降级提示）
- Agent 检索注入 + 引用来源展示

**未完成**：pgvector 索引下推（当前应用层余弦）、独立 rerank、混合检索 RRF。
**验收**：配置 embedding 模型后上传 PDF → 索引完成 → 检索命中 → Agent 回答带来源。

## 第五阶段：工作流 ✅ 已完成

- Vue Flow 编辑器（拖拽、连线、多选、缩放、小地图、自动布局、撤销重做）
- 9 类节点 + 右侧配置面板 + 上游变量选择
- 图 JSON 持久化 + 版本快照
- 后端 DAG 引擎（校验/拓扑/分支/超时/节点事件）
- SSE 实时节点状态 + 运行记录 + 节点轨迹

**验收**：Start → LLM → Condition → Answer 运行成功，节点逐个变色，运行记录可回看。

## 第六阶段：应用发布 ✅ 已完成

- 发布快照与版本号、API 开关、Key 生成（仅展示一次）
- 对外独立接口（对话/工作流、流式/非流式、session_id）
- 发布页：端点、密钥、curl/响应示例、调用日志入口

**验收**：curl 调用已发布 Agent 返回 JSON；`stream:true` 可收到 SSE 事件。

## 第七阶段：完善与优化 🟡 部分完成

- ✅ Dashboard 统计与图表、运行日志中心、Token 统计
- ✅ 38 个测试（引擎/工具/安全/API/知识处理）
- ✅ Docker 部署 + Alembic 迁移 + 文档
- ⬜ 公开分享页、多工作空间 RBAC、MCP 工具、Rerank、移动端适配、性能压测

## 后续演进优先级

| 优先级 | 事项 | 价值 |
| --- | --- | --- |
| P0 | pgvector `<=>` + HNSW 索引 | 检索性能从 O(n) 降到索引查询 |
| P0 | 公开 Web 分享页（免登录对话） | 业务方可直接试用 |
| P1 | Celery + Redis 任务队列 | 多实例并发处理文档 |
| P1 | 工作流子流程 / 循环节点 | 复杂业务编排 |
| P2 | MCP 工具接入 | 生态扩展 |
| P2 | 工作空间成员与权限 | 团队协作 |
