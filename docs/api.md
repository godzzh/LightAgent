# API 说明

- 前缀：`/api/v1`
- 鉴权：`Authorization: Bearer <JWT>`（除 `/health`、`/auth/login|register`、`/open/*`）
- 对外应用接口：`Authorization: Bearer <API Key>` 或 `X-API-Key`
- 统一响应：`{"code":0,"message":"success","data":{},"request_id":"..."}`
- 分页：`{"items":[],"total":100,"page":1,"page_size":20}`
- 错误码：400 参数 / 401 未认证 / 403 无权限 / 404 不存在 / 409 冲突 / 422 校验 / 500 服务端
- 完整交互式文档：`/docs`（Swagger UI）

## 认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/auth/register` | 注册并创建默认工作空间 |
| POST | `/auth/login` | 登录，返回 access_token |
| GET | `/auth/me` | 当前用户与工作空间 |
| PATCH | `/auth/me` | 修改用户名/密码 |
| POST | `/auth/logout` | 前端清 token |

## 工作空间

| GET | `/dashboard/overview` | 统计卡片 |
| GET | `/dashboard/recent` | 最近应用 + 最近运行 |
| GET | `/dashboard/trend` | 7 天趋势 + 模型分布 |

## 应用

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/applications` | 列表（keyword/app_type/status/分页） |
| GET | `/applications/templates` | 模板列表 |
| POST | `/applications` | 创建（可带 template） |
| GET | `/applications/{id}` | 详情 |
| PATCH | `/applications/{id}` | 更新（config 走 AgentConfig 校验） |
| DELETE | `/applications/{id}` | 删除 |
| POST | `/applications/{id}/copy` | 复制 |
| POST | `/applications/{id}/publish` | 发布（生成版本快照 + 可选新 Key） |
| POST | `/applications/{id}/unpublish` | 取消发布 |
| GET | `/applications/{id}/versions` | 版本快照 |
| GET/POST/DELETE | `/applications/{id}/keys` | API Key 管理 |
| GET | `/applications/{id}/stats` | 运行次数 / Token |

## Agent

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/agent/{app_id}/chat` | `stream=true` 返回 SSE；`false` 返回 JSON |
| GET | `/agent/applications/{app_id}/conversations` | 会话列表 |
| GET | `/agent/conversations/{id}/messages` | 会话消息 |
| DELETE | `/agent/conversations/{id}` | 删除会话 |
| GET | `/agent/runs` | 运行记录（app/status/keyword/分页） |
| GET | `/agent/runs/{run_id}` | 运行详情 + 执行轨迹 |

## 模型

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/models/presets` | 供应商预设 |
| GET/POST | `/models/providers` | 供应商列表 / 新增 |
| PATCH/DELETE | `/models/providers/{id}` | 更新 / 删除（api_key 留空不修改） |
| GET/POST | `/models/configs` | 模型配置列表 / 新增 |
| PATCH/DELETE | `/models/configs/{id}` | 更新 / 删除 |
| POST | `/models/test` | 连接测试（可传未保存的 key/base_url） |
| GET | `/models/available` | 可用于应用绑定的模型 |

## 知识库

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET/POST | `/knowledge/datasets` | 列表 / 创建 |
| GET/PATCH/DELETE | `/knowledge/datasets/{id}` | 详情 / 更新切片配置 / 删除 |
| GET | `/knowledge/datasets/{id}/documents` | 文档列表（含状态与进度） |
| POST | `/knowledge/datasets/{id}/documents` | 上传（multipart，异步处理） |
| DELETE | `/knowledge/documents/{id}` | 删除文档 |
| POST | `/knowledge/documents/{id}/reindex` | 重新索引 |
| GET | `/knowledge/documents/{id}/segments` | 切片列表 |
| PATCH | `/knowledge/segments/{id}` | 修改切片（重新向量化） |
| POST | `/knowledge/retrieve` | 检索测试（TopK / 阈值 / 降级提示） |
| POST | `/knowledge/datasets/{id}/preview-chunks` | 上传前切片预览 |

## 工具

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/tools` | 内置 + 自定义工具 |
| GET | `/tools/builtin` | 内置工具目录 |
| POST | `/tools` | 创建 HTTP 工具 |
| PATCH/DELETE | `/tools/{id}` | 更新 / 删除（内置禁止改删） |
| POST | `/tools/{id}/test` | 测试自定义工具 |
| POST | `/tools/builtin/{key}/test` | 测试内置工具 |

## 工作流

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/workflows/node-definitions` | 节点类型元数据 |
| GET/POST | `/workflows` | 列表 / 创建（自动生成基础画布） |
| GET/PATCH/DELETE | `/workflows/{id}` | 详情 / 保存（自动版本快照）/ 删除 |
| POST | `/workflows/{id}/validate` | 图校验 |
| POST | `/workflows/{id}/run` | `stream=true` SSE，否则阻塞返回 |
| GET | `/workflows/{id}/runs` | 运行记录 |
| GET | `/workflows/runs/{run_id}` | 运行详情 + 节点轨迹 |

## 日志

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/logs/runs` | `run_type=agent|workflow|llm`，支持 status/keyword/days/app_id |
| GET | `/logs/stats` | 调用次数 / Token / 平均延迟 |

## 对外 API（应用发布后）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/open/{app_id}/chat-messages` | Agent 对话（`stream` 可选） |
| POST | `/open/{app_id}/run` | 工作流应用执行 |
| GET | `/open/{app_id}/info` | 应用公开信息（欢迎语/开场问题） |

### 示例

```bash
# 非流式
curl -X POST http://localhost:8000/api/v1/open/<APP_ID>/chat-messages \
  -H "Authorization: Bearer <API_KEY>" -H "Content-Type: application/json" \
  -d '{"query":"你好","session_id":"u-1","stream":false}'

# 流式
curl -N -X POST http://localhost:8000/api/v1/open/<APP_ID>/chat-messages \
  -H "Authorization: Bearer <API_KEY>" -H "Content-Type: application/json" \
  -d '{"query":"你好","stream":true}'

# 工作流
curl -X POST http://localhost:8000/api/v1/open/<APP_ID>/run \
  -H "Authorization: Bearer <API_KEY>" -H "Content-Type: application/json" \
  -d '{"inputs":{"query":"整理这条工单"}}'
```
