# 页面覆盖：登录页 /login

> 本文件覆盖 `../MASTER.md` 的规则，构建登录页时优先采用。

## 设计依据

`ui-ux-pro-max` 检索结果：

```bash
python C:/Users/Admin/.workbuddy/skills/ui-ux-pro-max/scripts/search.py \
  "futuristic tech login authentication dark gradient" \
  --design-system -p "LightAgent Login" --variance 7 --motion 6 --density 4 -f markdown
```

- **Style**: `HUD / Sci-Fi FUI`（Futuristic, technical, wireframe, neon, data, transparency）
- **Pattern**: Immersive / Interactive Experience（深色背景聚焦、突出交互元素）
- **Key Effects**: Glow effects, scanning animations, ticker text, blinking markers, fine line drawing
- **Implementation Checklist**: 1px 细线、霓虹发光边框、等宽字体、深色/透明底、装饰性技术标记、全息感
- **Landing**: `--domain landing "authentication split screen"` 无匹配；重试 `"hero social proof"` 得到
  Hero + CTA 结构参考，据此采用「左品牌 Hero / 右认证表单」分栏。
- **UX**: `--domain ux "login form validation focus"` → 提交需 loading→success/error 反馈、
  输入必须有真实 `<label for>`（不可仅靠 placeholder）、blur 时内联校验。

## 与 MASTER.md 的差异（本项目约束优先）

| 项 | MASTER（后台） | 本页（登录） |
| --- | --- | --- |
| 主题 | 浅色 `#F5F7FA` | **深色** `#060B18`（仅登录页，`position:fixed` 全屏，不影响后台） |
| 强调色 | `#184CFF` | `#184CFF`（一致，不采用数据集的青色/绿色霓虹） |
| 字体 | 系统栈 | 系统栈 + 等宽字体仅用于技术标签/刻度（`--auth-mono`） |
| 圆角 | naive-ui 4px / 面板 8px | 相同（面板 8px、输入框与按钮 4px） |
| 布局 | 侧栏 + 顶栏 + 内容区 | 全屏分栏：顶部状态条 + 左 Hero + 右认证面板 |

## 实现要点（`frontend/src/views/auth/LoginView.vue`）

- 背景层：48px 网格（径向遮罩）、双径向光晕、扫描线纹理、单条缓慢扫描光带。
- 顶部 `auth-topbar`：品牌标识 + `SYSTEM ONLINE / SECURE GATEWAY` 状态刻字。
- 左侧 `auth-showcase`：eyebrow 徽标、渐变大标题、3 行 HUD 技术刻度、阶段标记。
- 右侧 `auth-panel`：半透明玻璃 + 1px 边框 + 四角括号 + 发光；
  `IDENTITY VERIFICATION` 徽标、真实 `<label for>`、深色 naive-ui 输入覆盖、发光主按钮。
- 动效克制（skill: 每屏 1–2 个关键动效）：仅面板入场淡入 + 背景扫描光带；
  `prefers-reduced-motion` 下两者均禁用。
- 无障碍：无 emoji、真实标签、可见焦点、等宽刻度为 `aria-hidden` 装饰、
  提交有 loading 态、错误由全局拦截器提示。
- 响应式：≤1024px 隐藏左侧展示区改为单栏；≤560px 收紧内边距与状态条。

## 业务逻辑（未改动）

登录 / 注册模式切换、`admin / admin123` 初始凭证提示、`redirect` 跳转、
token 写入与 `userStore.login` 全部保持原样。
