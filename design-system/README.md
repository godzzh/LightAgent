# LightAgent 设计系统

本目录由 `ui-ux-pro-max` skill 生成，作为后续页面开发的样式依据（Master + Overrides 模式）。

## 文件

| 文件 | 作用 |
| --- | --- |
| [lightagent/MASTER.md](lightagent/MASTER.md) | 全局设计规则（含 **项目覆盖约束**，优先级最高） |
| `lightagent/pages/` | 页面级覆盖规则（存在时覆盖 Master） |

## 使用方式

构建某个页面前，先读 `MASTER.md`，再检查 `lightagent/pages/[page-name].md` 是否存在；
存在则以页面文件为准，否则完全遵循 Master。

## 生成命令

```bash
python C:/Users/Admin/.workbuddy/skills/ui-ux-pro-max/scripts/search.py \
  "light mode saas admin dashboard clean professional" \
  --design-system --persist -p "LightAgent" \
  --variance 3 --motion 3 --density 8 \
  --output-dir "E:/LightAgent" -f markdown
```

## 重要说明

skill 数据集返回的通用配色（深色 `#0F172A` 系）与字体（Fira / JetBrains Mono）
**不适用于本项目**。用户已显式指定品牌约束，见 `MASTER.md` 顶部的「项目覆盖约束」：
主色 `#184CFF`、浅色主题、4px 圆角、系统字体栈。
本目录采纳的是其专业规则部分（极简 Swiss 企业后台风格、4/8 间距节奏、
hover 200–250ms、键盘可见焦点、4.5:1 文字对比度、reduced-motion、
错误 `role="alert"`、图表不单靠颜色区分系列等）。

## 已落地的优化

- `frontend/src/styles/index.css`：交互状态基线、语义错误色 token、动效时长 token、
  次级文字对比度提升、卡片 hover 阴影、表格横向滚动兜底、reduced-motion 补全。
- 全局 `cursor: pointer` / `:disabled` / `:focus-visible` 规范。
- 错误提示加 `role="alert"` + `aria-live`（Dashboard / 日志 / 运行详情 / 聊天气泡）。
- 「工作流」「知识库」列表的删除按钮由 hover-only 改为常驻可见、键盘可达、带无障碍名称。
- 侧栏激活项增加 3px 左侧指示条（不单靠颜色表达状态）。
- 图表：文字对比度提升到 AA、饼图直接标注系列名、容器加 `role="img"` + `aria-label`。
- **登录页重设计**：按 `HUD / Sci-Fi FUI` 风格（`--design-system` + `--domain style/ux/gsap/landing` 检索）
  重做 `/login`，深色全屏 + 网格/光晕/扫描线、左 Hero + 右认证面板分栏、四角 HUD 括号、
  等宽技术刻度；强调色仍为 `#184CFF`、naive-ui 圆角仍 4px、面板 8px；
  动效降级与 `<label for>` 等无障碍要求均已落实。详见 [lightagent/pages/login.md](lightagent/pages/login.md)。
