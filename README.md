# LightAgent · 轻量级 AI Agent 开发平台

一个**可真实运行**的轻量级 Dify 替代品：可视化配置 Agent、绑定知识库、挂载工具、编排工作流，并把应用发布成 API。

- 后端：FastAPI + SQLAlchemy 2.x + PostgreSQL/pgvector（本地可用 SQLite 快速启动）
- 前端：Vue 3 + TypeScript + Vite + Naive UI + Tailwind + Vue Flow + ECharts + Monaco
- 模型：统一 Provider 抽象，主推 DeepSeek（OpenAI 兼容协议）
- 执行：自研 Agent Runtime（Function Calling / ReAct）+ 自研 DAG 工作流引擎，全部后端真实执行

---

## 一、5 分钟跑起来（本地开发模式）

> 本地模式默认使用 SQLite，无需 Docker / PostgreSQL 即可完整体验除数据库差异外的全部功能。

### 1. 后端

```bash
cd backend
cp .env.example .env          # Windows: copy .env.example .env
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

<details>
<summary><b>Windows 常见问题：提示 “pip 不是内部或外部命令” / 下载超时</b></summary>

1. **`pip` 命令找不到**：说明当前 Shell 没有激活虚拟环境，或系统 Python 未把 `Scripts` 加入 PATH。
   两种可用写法（任选其一）：

   ```bat
   :: 写法一：先激活虚拟环境，pip 会随激活自动生效
   .venv\Scripts\activate
   pip install -r requirements.txt

   :: 写法二：不激活，直接用解释器调用 pip（最稳）
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. **下载慢或 `No matching distribution found`**：多为网络/代理问题，换国内镜像即可：

   ```bat
   .venv\Scripts\python.exe -m pip install -r requirements.txt ^
     -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

3. 启动后端同理，若 `uvicorn` 命令不可用，用 `.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`。

</details>

启动时会自动建表、注册 6 个内置工具，并在首次启动时创建管理员账号：

| 账号 | 密码 |
| --- | --- |
| `admin` | `admin123` |

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

### 2. 前端

```bash
cd frontend
cp .env.example .env          # 可选，默认 /api/v1
npm install
npm run dev
```

打开 http://127.0.0.1:5173 ，用 `admin / admin123` 登录。

### 3. 接入 DeepSeek（关键一步）

1. 进入「模型管理」→ 添加供应商，类型选 `DeepSeek`，填入 `sk-...`，点「测试连接」。
2. 点「添加模型」：显示名 `DeepSeek Chat`、模型名 `deepseek-chat`（推理模型用 `deepseek-reasoner`），设为默认。
3. 进入「应用管理」→ 新建应用（模板选「数据助手」或「客服助手」）。
4. 在 Agent 调试页选择模型 → 发送消息，即可看到**真实流式回答**；勾选工具后可直接触发 Function Calling。
5. 知识库 RAG 需要额外配置一个 **Embedding 模型**（DeepSeek 不提供 embedding 接口），
   可在「模型管理」用 OpenAI 兼容接口添加（如 `text-embedding-3-small` 或本地 bge-m3 网关）。

---

## 二、Docker Compose 部署（生产形态）

```bash
cp backend/.env.example backend/.env
# 修改 backend/.env 里的 SECRET_KEY（务必改成随机字符串）
docker compose up -d --build
# 打开 http://localhost:8080
```

包含 6 个服务：

| 服务 | 说明 |
| --- | --- |
| postgres | `pgvector/pgvector:pg16`，已启用 vector 扩展 |
| redis | 缓存与后续任务协调（当前 worker 采用 DB 轮询，可平滑替换 Celery） |
| backend | FastAPI，启动前执行 `alembic upgrade head` |
| worker | 文档解析/切片/向量化后台进程 |
| frontend | 多阶段构建，Nginx 托管静态资源并代理 `/api` |
| nginx | 统一入口（8080），SSE 已关闭缓冲 |

数据库迁移：

```bash
# 容器内已自动执行；手动执行方式
docker compose exec backend alembic upgrade head
# 生成新迁移
docker compose exec backend alembic revision --autogenerate -m "add xxx"
```

---

## 三、功能清单（均已实现真实后端）

### 工作空间 Dashboard
统计卡片（应用/已发布/知识库/工作流/运行次数/Token）、最近应用、最近运行、7 天调用趋势、模型使用分布、快速入口；含 Loading / Empty / Error 三态。

### 应用管理
三种类型（Chat Agent / Chatbot / Workflow）、4 套模板、CRUD、复制、发布/取消发布、版本快照、运行日志入口。

### Agent（核心）
- 配置：系统提示词、User Prompt 模板、欢迎语、开场问题、模型绑定、Temperature / Top P / Max Tokens、最大步数、最大工具调用数、上下文记忆、工具、知识库、变量
- Prompt 变量自动识别 `{{var}}`，支持 `{{query}}` / `{{knowledge_context}}`
- 调试页三栏布局：左配置 / 中对话（Markdown、代码高亮、流式、停止、重新生成、复制）/ 右运行详情（模型、Token、耗时、工具入参出参、知识召回、错误）
- 执行引擎：原生 Tool Calling 优先，ReAct 文本解析兜底；受控的最大步数 / 调用次数 / 单工具超时 / 整体超时

### 模型管理
统一 Provider 抽象（`BaseLLMProvider`）、DeepSeek / OpenAI / OpenAI 兼容、预留通义/智谱/Moonshot/Ollama；API Key Fernet 加密存储且只返回脱敏串；连接测试；LLM / Embedding 双类型；默认模型。

### 知识库（RAG）
数据集 CRUD、PDF / DOCX / TXT / Markdown / HTML 解析、4 种切片策略（固定长度 / 段落 / 标题 / 自定义分隔符）、切片预览、上传后异步流水线（waiting→parsing→splitting→indexing→completed/failed，带进度与失败原因）、重新索引、切片查看与修改（改后重新向量化）、检索测试（Top K / 阈值 / 相似度分数 / 来源）。

### 工具管理
Tool Registry（register / unregister / get / list / execute）、6 个内置工具（时间、日期计算、数学计算、HTTP 请求、JSON 解析、文本处理）、可视化自定义 HTTP 工具（自动转 Function Calling Schema）、在线测试、SSRF 防护。

### 工作流（核心）
Vue Flow 三栏编辑器：节点面板 / 画布 / 配置面板；9 种节点（Start、LLM、Knowledge、HTTP、Code、Condition、Variable、Answer、End）；变量系统 `{{node_id.field}}`；保存 / 撤销 / 重做 / 自动布局 / 校验 / 运行；后端 DAG 引擎（校验→拓扑排序→按依赖执行→条件分支→事件推送）；节点状态实时着色（运行中/成功/失败/跳过）；运行记录与节点轨迹。

### 应用发布
发布快照 + 版本号、API Key（仅创建时明文展示一次，库中只存 SHA256）、独立对外接口（`/api/v1/open/...`）、流式与非流式、会话 ID、调用示例、Call Log。

### 运行日志
Agent / Workflow / LLM 三类日志统一查询，支持关键词、状态、时间范围、应用过滤；详情含执行轨迹与节点输入输出；Token 与平均耗时统计。

---

## 三之二、界面设计系统（iOS 风格）

前端视觉按 Apple Human Interface Guidelines 重构，设计 token 集中在两处，改主题不必逐页改代码：

| 文件 | 作用 |
| --- | --- |
| `frontend/tailwind.config.js` | 颜色、圆角、阴影、弹簧曲线等 Tailwind token |
| `frontend/src/styles/index.css` | CSS 变量 + 组件类 + Naive UI 全局覆盖 |
| `frontend/src/App.vue` | Naive UI `themeOverrides`（按钮/输入/表格/弹窗/标签） |

**核心规范**

- **配色**：系统蓝 `#007AFF` 主色，`#F2F2F7` 分组背景，`#1C1C1E` 主文字，`rgba(60,60,67,.13)` 分割线；语义色用系统绿 `#34C759`、橙 `#FF9500`、红 `#FF3B30`。
- **字体**：`-apple-system / SF Pro / PingFang SC` 系统栈，标题收紧字距（`-0.022em`），符合 iOS 排版习惯。
- **形状**：卡片 18px、分组 12px、控件 10px 连续圆角；阴影极轻（`0 1px 2px` + 大扩散低透明），靠留白和层次而非投影。
- **材质**：导航栏与浮层使用 Liquid Glass 轻量版（`backdrop-filter: blur(24px) saturate(180%)` + 72% 白），已提供 `prefers-reduced-transparency` 退化方案。
- **列表**：`.la-list` + `.la-row` 实现 iOS inset-grouped 列表（52px 行高、行间 0.5px 分割线、hover 变色、按压反馈）。
- **动效**：统一弹簧曲线 `cubic-bezier(.32,.72,0,1)`，按压 `scale(.975)`，且不改变布局盒尺寸；完整支持 `prefers-reduced-motion`。

**复用类**：`.la-card`（分组卡片）、`.la-page`（页面容器）、`.la-title`（大标题）、`.la-section-label`（分组标签）、`.la-pill`（状态胶囊）、`.la-icon-tile`（App 图标）、`.la-tile`（悬浮入口）、`.la-glass`（毛玻璃）、`.la-search`（iOS 搜索框）、`.la-typing`（打字指示器）。

---

## 四、目录结构

```
LightAgent/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # auth / applications / agent / models / knowledge / tools / workflows / logs / dashboard / public
│   │   ├── core/            # 配置、数据库、安全、加密、异常、日志、统一响应、初始化数据
│   │   ├── models/          # SQLAlchemy 模型（18 张表）
│   │   ├── schemas/         # Pydantic v2 校验模型
│   │   ├── services/        # agent / workflow / knowledge / tools / workspace
│   │   ├── engines/         # agent_runtime、workflow_engine、nodes、variable_resolver、safe_eval
│   │   ├── providers/       # base、deepseek、openai_compatible、registry
│   │   ├── tool_registry/   # registry、builtin、custom
│   │   ├── tasks/           # worker（文档处理）
│   │   └── main.py
│   ├── migrations/          # Alembic（初始迁移已生成）
│   └── tests/               # 38 个单元/集成测试
├── frontend/
│   └── src/
│       ├── api/             # axios 封装 + SSE 流读取
│       ├── components/      # common / agent / workflow
│       ├── views/           # dashboard / applications / agent / knowledge / tools / models / workflow / logs / settings / auth
│       ├── layouts / router / stores / types / utils / styles
├── nginx/nginx.conf
├── docker-compose.yml
└── docs/                    # 架构、数据库、API、路线图
```

---

## 五、验证方式

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q      # Windows
# 或 pytest -q
```

当前结果：**38 passed**，覆盖工具安全、SSRF 防护、受限表达式、Agent Runtime（流式/工具调用/步数上限/ReAct）、工作流 DAG（校验/环检测/条件分支/变量/Code 节点）、知识库解析切片、API 集成。

手工验收路径：

1. 登录 → Dashboard 数据为 0（空状态）
2. 模型管理添加 DeepSeek → 测试连接成功
3. 新建 Agent → 调试页发问 → 流式回答 + Token/耗时
4. 勾选「数学计算」工具 → 问「(12+8)*3/4 等于多少」→ 观察 tool_call / tool_result
5. 新建知识库 → 上传 PDF → 配置 Embedding 模型后索引完成 → 检索测试命中 → Agent 绑定后回答带来源
6. 新建工作流 Start → LLM → Condition → Answer → 运行 → 节点逐个变色 + 运行记录
7. 应用发布 → 拿 API Key → 用 curl 调 `/api/v1/open/{app_id}/chat-messages` 成功返回

curl 示例：

```bash
curl -X POST http://localhost:8000/api/v1/open/<APP_ID>/chat-messages \
  -H "Authorization: Bearer <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"query": "你好，介绍一下你能做什么", "session_id": "user-001", "stream": false}'
```

---

## 六、已知限制（诚实说明）

1. **Embedding 依赖外部模型**：DeepSeek 无 embedding 接口，未配置 embedding 模型时文档会以 `failed` 状态结束并给出明确原因，检索测试自动降级为关键词匹配。
2. **向量检索当前在应用层计算余弦相似度**（SQLite / PostgreSQL 行为一致）。`docker-compose` 已启用 pgvector 并创建扩展，数据量上万后建议把 `services/knowledge/index.py` 的排序下推到 pgvector `<=>` + HNSW 索引，接口无需改动。
3. **本地模式使用 SQLite + 进程内后台任务**；Redis / Celery 仅在 Docker 形态下提供（worker 目前是 DB 轮询，可无缝换 Celery）。
4. **Code 节点是受限表达式求值**（AST 白名单，不用 eval/exec），不支持任意 Python；如需完整代码沙箱建议独立容器执行。
5. 未实现多租户 RBAC 细粒度权限（当前一个用户一个默认工作空间）、未实现 MCP 工具与 Rerank。
6. 前端未做移动端适配（以桌面管理后台为主）。

---

## 七、下一步

- pgvector 原生检索 + 混合检索（向量 + 关键词 RRF）
- 应用对话的公开分享页（免登录 Web 端）
- Celery + Redis 任务化文档处理，支持并发限流
- MCP 工具接入、Rerank 模型、工作流循环/子流程节点
- 多工作空间与成员权限

更详细的设计见 `docs/`：`architecture.md`、`database.md`、`api.md`、`roadmap.md`。
