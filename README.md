# AI 角色扮演情感引擎

> 轻量级、零服务器的 AI 角色扮演框架。7 个 Python 脚本 + JSON 配置 = 完整的情感追踪引擎。
>
> **核心理念：工具管数值，AI 只管演。**
>
> 运行于 Claude Code 等 AI 编程助手中——AI 阅读 ENGINE.md 获取操作规则，通过 CLI 调用 Python 脚本读写本地 JSON 文件。引擎本身无需服务器、无需 API Key、无网络依赖。

[English](README_EN.md)

---

## 这是什么

一个为 AI 角色扮演设计的情感追踪引擎。它用三个数值维度（信任、亲近、温度）量化角色与用户的关系状态，通过关键词匹配自动更新数值，驱动 AI 在不同关系阶段表现出不同的行为模式。

如果你已经部署了`Claude`，并且已经在用 ta 做许多事情，为什么不让 ta 的交互更精彩一些呢？只需要下载几个文件，并在`CLAUDE.md`上加上调用说明，就可以消耗少量token，来培养一个情感丰富的AI助手。

**你不写 Prompt，引擎帮你驱动 Prompt。**

---

## 特性

- **三维情感模型**：信任度 (trust) + 亲近度 (closeness) + 温度 (warmth)，加权映射四阶段
- **EMA 平滑**：防止单次互动造成情感剧烈跳变，模拟人类"慢热慢冷"的惯性
- **指数衰减**：长时间不互动，情感自然降温（三维各自独立的半衰期）
- **批量操作**：`batch.py` 将每轮对话的多次脚本调用合并为一次，state.json 仅读写一轮
- **AI 自我完善**：对话中自动发现角色偏好，写入配置，无需手动编辑 JSON
- **四档处理深度**：从零 token 纯工具到深度思考，按需切换
- **公私分离**：引擎公开，角色私有——切换角色只需替换 `settings/` 下的两个 `character_*` 文件
- **多语言**：引擎文档 + README 提供中英双版

---

## 怎么用

### 第一步：下载引擎文件

将以下文件/文件夹复制到你用于存放引擎的目录（如 `D:\engines\roleplay\`）：

```
ENGINE.md              ← AI 操作手册（中文）
ENGINE_EN.md           ← AI 操作手册（英文）
settings/              ← 角色设定目录（下面第二步细说）
tool/                  ← 全部 7 个 Python 脚本（必须）
```

`README.md` 和 `CLAUDE.md` 不需要复制——README 是给你看的，CLAUDE.md 放在你自己的项目里（第四步）。

### 第二步：选择语言设定

`settings/` 下提供了中英两份预设，选一份去掉后缀即可：

| 你想要的语言 | 操作 |
|-------------|------|
| 中文 | `character_config_zh.json` → 重命名为 `character_config.json` |
| | `character_profile_zh.md` → 重命名为 `character_profile.md` |
| English | `character_config_en.json` → rename to `character_config.json` |
| | `character_profile_en.md` → rename to `character_profile.md` |

> 引擎只认 `character_config.json` 和 `character_profile.md` 这两个固定文件名，所以必须改名。多余的语言文件（如 `_en.json`）删掉或留着都行，引擎不读它们。

### 第三步：确认最终目录

改完名后，你的引擎目录应该长这样：

```
D:\engines\roleplay\
├── ENGINE.md              ← AI 操作手册（中文）
├── ENGINE_EN.md           ← AI 操作手册（英文）
├── tool/                  ← 引擎脚本
│   ├── batch.py
│   ├── process_event.py
│   ├── get_context.py
│   ├── add_preference.py
│   ├── add_memory.py
│   ├── record_action.py
│   └── add_custom_item.py
└── settings/
    ├── character_profile.md   ← 角色人格（已改名）
    ├── character_config.json  ← 情感模型（已改名）
    └── state.json             ← 自动生成，不用手动创建
```

### 第四步：配置 CLAUDE.md

在你**自己的项目根目录**下创建或编辑 `CLAUDE.md`，加入以下内容：

```markdown
## Role-Play Engine

引擎根目录: D:\engines\roleplay

务必按顺序阅读以下文件以启用角色扮演功能：
1. {引擎根目录}\ENGINE.md — 工具使用规则、处理档位、行为阶段指引
2. {引擎根目录}\settings\character_profile.md — 角色人格、说话模式、动作神态

所有脚本路径以引擎根目录为基准，ENGINE.md 中有完整的脚本调用表。
```

> **路径写成你自己的绝对路径**，如 `C:\Users\你的用户名\Documents\roleplay`。用英文版 ENGINE 的话，第一行改为 `ENGINE_EN.md`。

### 第五步：初始化并开始

```bash
python tool/get_context.py
```

脚本会自动创建 `settings/state.json`。然后直接开始和角色对话即可——AI 会自动获取上下文、处理事件、记录记忆和动作。

---

## 自定义角色设定

预设的灰原哀设定可以直接用，也可以改成你自己的角色。

### 修改情感模型（character_config.json）

| 字段 | 作用 | 怎么改 |
|------|------|--------|
| `dimensions` | 三维情感基线、半衰期、范围 | 调整数值；信任半衰期越长越难涨跌 |
| `event_table` | 关键词 → 情感增量 | 按你的角色写触发词和 delta 值 |
| `stages` | 四个阶段名称 | 改成适合你角色的阶段名 |
| `stage_guides` | 每个阶段的行为指引 | 告诉 AI 该阶段应该怎么演 |
| `processing_level` | 处理深度 (0-3) | 初次配角色用 3，日常用 1，稳定用 0 |

### 修改角色人格（character_profile.md）

按模板格式写：身份、性格、说话风格、动作池、特殊触发。参考预设文件的结构即可。

### 切换角色

1. 替换 `settings/character_config.json` 为新角色
2. 替换 `settings/character_profile.md` 为新角色
3. 删除 `settings/state.json`（重置情感状态）
4. 引擎脚本（`tool/`）**一行不动**

---

## 切换语言

1. 把目标语言的设定文件改名（如 `character_config_en.json` → `character_config.json`）
2. 同理改 `character_profile_*.md` → `character_profile.md`
3. 删除 `state.json`（语言不同，旧记忆无法迁移）
4. 把 `CLAUDE.md` 里的 `ENGINE.md` 改成 `ENGINE_EN.md`（反之亦然）

> **注意**：`character_config.json` 和 `character_profile.md` 是引擎硬编码的文件名，必须精确使用这两个名字，不要改源码中的文件名引用。`state.json` 存的是运行时数据，语言切换后旧记忆和动作历史无法迁移，必须重置。

---

## 什么原理

### 三维情感模型

| 维度 | 范围 | 含义 | 默认半衰期 |
|------|:---:|------|:---:|
| **trust** (信任) | 0–100 | 对用户能力/可靠性的认可 | 60 天 |
| **closeness** (亲近) | 0–100 | 情感距离，愿不愿并肩 | 14 天 |
| **warmth** (温度) | -100~100 | 语气冷热，正=软/负=刺 | 7 天 |

三维加权映射到四个关系阶段（陌生 → 同僚 → 同伴 → 珍视），阶段名称和行为指引可在 `character_config.json` 中自定义。

### 处理流程

```
用户输入 → AI 描述事件（≤20字）
         → 关键词匹配（遍历 event_table，按优先级，先匹配先生效）
         → 计算距上次互动天数 → 指数衰减
         → EMA 平滑叠加 → 限幅到合法范围
         → 更新 state.json → 输出阶段 + 行为指引
```

### 衰减公式

长时间不互动，情感自然回落至基线：

```
V = baseline + (V_current - baseline) × e^(-k × days)
k = ln(2) / half_life_days
```

- trust 半衰期最长（60 天）—— 信任来去都慢
- warmth 半衰期最短（7 天）—— 温度波动最快

### EMA 平滑

防止单次事件造成数值剧烈跳变：

```
new = old + event_delta × α    （α 默认 0.3）
```

事件 delta 不会直接全额生效，而是乘以平滑系数缓慢累积，模拟人类情感的惯性。

---

## 效果示例

以下以「毛利兰」为例，展示几轮对话中引擎如何实时驱动情感变化。

> 初始：信任 55 / 亲近 40 / 温度 30 — **初见**阶段

```
用户："你好！我是新搬来的邻居，请多关照～"

事件：初次见面打招呼
匹配：日常互动 → trust+0, closeness+0.35, warmth+0.35  (×α=0.35)
─────────────────────────────────────────────────
信任 55 → 55    亲近 40 → 40    温度 30 → 30
阶段：初见 — "礼貌但保持距离，用敬语，笑容客气而节制"

兰：（微微欠身，笑容礼貌而节制）
   "您好，我是毛利兰。请多关照。有什么需要帮忙的随时说哦。"
```

```
用户："听说你做便当很厉害？今天试着做了一份，给你尝尝"

事件：用户分享料理给兰
匹配：料理/分享食物 → trust+0, closeness+1.05, warmth+1.4  (×α=0.35)
─────────────────────────────────────────────────
信任 56 → 56    亲近 43 → 44    温度 33 → 34
阶段：朋友 — "语气轻松自然，会主动聊起日常小事，笑容真诚"

兰：（眼睛一亮，双手接过便当盒）
   "诶～好香！你手艺很不错嘛。下次我也给你带一份我做的，算是回礼啦。"
```

```
用户："别担心，我会保护你的。谁也别想伤害你。"

事件：用户坚定地保护兰
匹配：被保护/守护 → trust+0.7, closeness+2.1, warmth+1.75  (×α=0.35)
─────────────────────────────────────────────────
信任 57 → 58    亲近 46 → 48    温度 35 → 37
阶段：好友 — "主动邀约一起吃饭或出行，会为对方准备便当，关心溢于言表"

兰：（微微脸红，随后露出温暖的笑容）
   "谢谢…能遇到你真的很幸运。对了，周末有空吗？我们一起去看花火大会吧，便当我来准备。"
```

> 从客气微笑到主动分享便当再到并肩而立——**同一套引擎，三次关键词匹配，三种截然不同的兰。**

---


在 `character_config.json` 中设置 `processing_level` (0-3)，控制 AI 的分析深度和 token 消耗：

| 档位 | Token | AI 行为 |
|:---:|:---:|------|
| **0** | 零 | 纯工具：AI 不分析不提议，只表演 |
| **1** | 低 | 标准：AI 可补充缺失关键词 |
| **2** | 中 | 辅助：AI 可改写事件、提议权重 |
| **3** | 高 | 深度：AI 自由分析语义、质疑规则 |

建议：初始设计角色配置用 Level 3，日常使用用 Level 1，长期稳定后用 Level 0。

---

## 依赖

- Python 3.7+
- 零第三方库（仅标准库：`json`、`os`、`sys`、`math`、`datetime`）

## License

MIT
