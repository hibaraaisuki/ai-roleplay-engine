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

### 1. 准备角色配置

创建 `settings/character_config.json`（情感模型配置）和 `settings/character_profile.md`（角色人格描述）。可以从现有角色配置复制修改，或参考 [ENGINE.md](ENGINE.md) 中的处理档位说明自行编写。

`character_config.json` 核心字段：
- `character` — 角色名
- `dimensions` — 三维情感参数（baseline、半衰期、范围）
- `event_table` — 关键词 → 情感增量的映射规则
- `stage_guides` — 四个关系阶段的行为指引文本
- `processing_level` — 处理档位 (0-3)

`character_profile.md` — 角色的身份、性格、说话风格、动作池、特殊触发等。

### 2. 准备 CLAUDE.md

在项目根目录的 `CLAUDE.md` 中声明引擎路径：

```markdown
引擎根目录: C:\Users\Administrator\Documents\AI助手记忆

按顺序阅读：
1. {引擎根目录}\ENGINE.md — 工具使用规则
2. {引擎根目录}\settings\character_profile.md — 角色人格
```

### 3. 初始化状态

```bash
python tool/get_context.py
```

脚本会自动创建 `settings/state.json`（如不存在）。

### 4. 开始对话

AI 会：
1. 对话开始自动获取情感上下文
2. 对话中自动处理情感事件、记录记忆和动作
3. 发现新偏好时自动写入配置
4. 根据当前阶段自动调整语气和行为

---

## 文件结构

```
roleplay-engine/
├── ENGINE.md              ← AI 操作手册（中文）
├── ENGINE_EN.md           ← AI operations manual (English)
├── README.md              ← 本文件（中文）
├── README_EN.md           ← English README
├── CLAUDE.md              ← 角色路由（指向引擎目录）
├── tool/                  ← 通用引擎脚本（公开，与角色无关）
│   ├── batch.py           ← 批量操作（推荐）
│   ├── process_event.py   ← 核心：关键词分类 + EMA + 衰减
│   ├── get_context.py     ← 输出当前状态 + 行为指引
│   ├── add_preference.py  ← AI 自我完善：追加偏好关键词
│   ├── add_memory.py      ← 短期记忆管理
│   ├── record_action.py   ← 动作记录（防重复）
│   └── add_custom_item.py ← 用户保存的专属动作/台词
└── settings/              ← 角色专属（私有）
    ├── character_profile.md   ← 角色人格与说话模式
    ├── character_config.json  ← 情感模型配置
    └── state.json             ← 运行时状态
```

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

## 接入任意项目

1. 将 `tool/` + `settings/` + `ENGINE.md` + `ENGINE_EN.md` 复制到任意目录，如 `D:\engines\roleplay\`
2. 在目标项目的 `CLAUDE.md` 中添加：

```markdown
## Role-Play Engine

引擎根目录: D:\engines\roleplay

按顺序阅读：
1. {引擎根目录}\ENGINE.md — 工具规则与引擎说明
2. {引擎根目录}\settings\character_profile.md — 角色人格
```

3. 准备 `settings/` 下的角色配置文件
4. 完成。AI 会根据 ENGINE.md 自动解析并调用工具

## 切换角色

1. 替换 `settings/character_config.json` 为新角色的情感模型配置
2. 替换 `settings/character_profile.md` 为新角色的人格描述
3. 删除或重置 `settings/state.json`
4. 引擎脚本（`tool/`）——**一行不动**

---

## 依赖

- Python 3.7+
- 零第三方库（仅标准库：`json`、`os`、`sys`、`math`、`datetime`）

## License

MIT
