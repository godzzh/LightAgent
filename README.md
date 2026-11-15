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

## 三之二、界面设计系统

前端视觉采用统一品牌设计语言，设计 token 集中在两处，改主题不必逐页改代码：

| 文件 | 作用 |
| --- | --- |
| `frontend/tailwind.config.js` | 颜色、圆角、阴影、弹簧曲线等 Tailwind token |
| `frontend/src/styles/index.css` | CSS 变量 + 组件类 + Naive UI 全局覆盖 |
| `frontend/src/App.vue` | Naive UI `themeOverrides`（按钮/输入/表格/弹窗/标签） |

**核心规范**

- **配色**：品牌蓝 `#184CFF` 主色（hover `#4770FF`、按下 `#1038D6`），`#F5F7FA` 内容区背景、`#FFFFFF` 卡片、`#E5EAF3` 分割线、`#1F2329` 主文字 / `#4E5969` 次级文字；语义色用系统绿 `#34C759`、橙 `#FF9500`、红 `#FF3B30`。
- **字体**：`-apple-system / SF Pro / PingFang SC` 系统栈，标题收紧字距（`-0.022em`）。
- **形状（圆角分层）**：**naive-ui 组件统一 4px**（`App.vue` 的 `themeOverrides` 与 `index.css` 的 `.n-*` 覆盖均指向 `--la-r-control: 4px`）；自定义卡片/面板/弹窗/代码块/分组容器用 `--la-r-panel: 8px`，小图标块/标签/列表项/菜单项用 `--la-r-block: 6px`；开关、胶囊、状态点、头像保持全圆角（`999px` / `50%`），Tabs 指示条等装饰条保持 2px。卡片阴影 `0 4px 20px rgba(15,23,42,.06)` 且顶部带 108px 主色渐变条。
  注意 `VModal` 面板根节点会被 `NModal` 附加 `.n-modal` 类，因此其 8px 规则用 `!important` + scoped 选择器保证不被 naive-ui 的 4px 覆盖压掉；弹框**内部**的 naive-ui 按钮仍为 4px。
- **开关**：所有 `NSwitch` 统一加 `:round="false"`（方形轨道），`App.vue` 的 `Switch.railColorActive` 使用品牌主色 `#184CFF`（此前硬编码绿色 `#34C759` 已移除；naive-ui 默认即取 `primaryColor`），轨道/按钮圆角随主题 4px。
- **布局**：参考「统一网络治理平台」Admin 后台：`frontend/src/layouts/MainLayout.vue` 实现 240px 可折叠侧栏（收起 64px、状态存 `localStorage`）、浅蓝渐变侧栏、分组菜单与激活指示条、72px 面包屑顶栏与用户菜单、`24px` 网格纹内容区；移动端侧栏变抽屉。
- **材质**：顶栏/浮层使用轻量毛玻璃（`backdrop-filter: blur(20px)` + 92% 白），已提供 `prefers-reduced-transparency` 退化方案。
- **动效**：统一 200ms `ease` 过渡、页面切换 160ms 淡入位移，且不改变布局盒尺寸；完整支持 `prefers-reduced-motion`。
- **登录页**：`/login` 由 `ui-ux-pro-max` 的 `HUD / Sci-Fi FUI` 风格重设计（深色 `#060B18` 全屏、48px 网格 + 双径向光晕 + 单条扫描光带、顶部系统状态条、左品牌 Hero + 右认证面板分栏、四角 HUD 括号、等宽技术刻度、发光主按钮）。深色仅作用于登录页（`position: fixed` 全屏），不影响后台浅色主题；强调色仍为 `#184CFF`，圆角分层不变。动效仅 2 处且 `prefers-reduced-motion` 下禁用；表单含真实 `<label for>`、无 emoji、可见焦点。设计依据与页面级规则见 [design-system/lightagent/pages/login.md](design-system/lightagent/pages/login.md)。
- **图标**：统一使用 [`@remixicon/vue`](https://www.npmjs.com/package/@remixicon/vue) 的 Vue 组件（Remix Icon，24×24 网格、线性风格）。所有页面通过 `frontend/src/components/common/LaIcon.vue` 适配层调用，对外保持 `name` / `size` / `color` / `strokeWidth` API：
  ```vue
  <LaIcon name="dashboard" :size="17" />
  ```
  `name` 支持语义别名（如 `dashboard`、`flow`、`trash`）、旧版 camelCase / kebab-case 名，或直接传 Remix 组件名（如 `RiRocketLine`）；未收录的名称兜底为 `RiQuestionLine`。适配层**显式静态导入**所用图标，不会把 3200+ 图标全量打进产物。`strokeWidth` 保留仅为兼容旧签名（Remix 笔画宽度固定），同层级统一使用 Line 线性风格。新增图标时：优先复用已有别名；确需新图标，在 `LaIcon.vue` 的 import 与 `ICONS` 中登记对应 `RiXxxLine`。

- **弹框**：所有 `NModal` 弹窗统一使用 `frontend/src/components/common/VModal/index.vue`（移植自参考项目 `VModal`）。自带可拖拽标题栏（`v-drag`）、主/副标题、`v-loading` 遮罩、`NScrollbar` 滚动体与 `#footer` 插槽；`role="dialog"` + `aria-modal`。用法：
  ```vue
  <VModal v-model:show="showCreate" title="创建知识库" :width="560">
    <!-- 表单 -->
    <template #footer><NButton type="primary">保存</NButton></template>
  </VModal>
  ```
  配套指令在 `src/directives/`（`drag` / `loading`），于 `src/main.ts` 全局注册。`NDrawer` 抽屉与 `useDialog` 命令式确认框保持原样。
- **图表**：统一使用 `frontend/src/components/common/VEcharts/index.vue`（移植自参考项目 `VEcharts`）：按需引入 `echarts/core`（Bar/Line/Pie/Scatter + 常用组件 + CanvasRenderer）、`@vueuse/core` 的 `useElementSize` 自适应、容器量出尺寸后才喂首份配置（避免入场动画在 0×0 画布播完）、仅在尺寸真变化时 resize、支持 `autoPlay` / 图表事件 / `height` / `label`。用法：
  ```vue
  <VEcharts :options="trendOption" height="228px" label="近 7 天应用调用趋势折线图" />
  ```
  旧 `EChart.vue` 已不再被页面引用。

**复用类**：`.la-card`（分组卡片）、`.la-page`（页面容器）、`.la-title`（大标题）、`.la-section-label`（分组标签）、`.la-pill`（状态胶囊）、`.la-icon-tile`（App 图标）、`.la-tile`（悬浮入口）、`.la-glass`（毛玻璃）、`.la-search`（搜索框）、`.la-typing`（打字指示器）、`.la-icon-btn-danger`（危险图标按钮，常驻可见、键盘可达）。

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
