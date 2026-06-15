# ENGINE.md — 角色扮演情感引擎

> **轻量级、零服务器的 AI 角色扮演框架。**
> 7 个 Python 脚本 + JSON 配置 + 本文档 = 完整的情感追踪引擎。
>
> **核心理念：工具管数值，AI 只管演。**

[English](ENGINE_EN.md)

---

## 目录结构

> `{ENGINE_ROOT}` = 本文件所在目录的绝对路径。由项目 `CLAUDE.md` 中声明。

```
{ENGINE_ROOT}/
├── ENGINE.md              ← 本文件（引擎规则说明书）
├── ENGINE_EN.md           ← 英文版引擎规则
├── tool/                  ← 通用引擎脚本（静态，与角色无关）
│   ├── batch.py           ← 批量操作（推荐）：合并多操作为单次调用
│   ├── process_event.py   ← 核心：关键词分类 + EMA + 衰减
│   ├── get_context.py     ← 输出当前状态 + 行为指引
│   ├── add_preference.py  ← AI 自我完善：追加偏好关键词
│   ├── add_memory.py      ← 短期记忆管理
│   ├── record_action.py   ← 动作记录（防重复）
│   └── add_custom_item.py ← 用户保存的专属动作/台词
└── settings/              ← 角色专属（按角色私有）
    ├── character_profile.md   ← 角色人格与说话模式（私有）
    ├── character_config.json  ← 情感模型配置（私有）
    └── state.json             ← 运行时状态（私有）
```

- **`tool/`** — 静态通用脚本。逻辑修改通过 `settings/` 中的配置引导，无需改脚本。
- **`settings/`** — 角色专属：人格描述、情感模型参数、偏好、记忆、运行时状态。
- 脚本通过 `__file__` 自动解析 `settings/` 相对路径 — **无硬编码路径**。

---

## 脚本调用表

| 用途 | 命令 |
|------|------|
| **批量操作（推荐）** | `echo '[...]' \| python "{ENGINE_ROOT}/tool/batch.py"` |
| 获取上下文 | `python "{ENGINE_ROOT}/tool/get_context.py" --json` |
| 处理事件 | `python "{ENGINE_ROOT}/tool/process_event.py" --json "<事件描述>"` |
| 添加偏好 | `python "{ENGINE_ROOT}/tool/add_preference.py" <like\|dislike\|trigger\|keyword> "<内容>"` |
| 添加记忆 | `python "{ENGINE_ROOT}/tool/add_memory.py" "<文本>"` |
| 记录动作 | `python "{ENGINE_ROOT}/tool/record_action.py" "<动作>"` |
| 保存专属条目 | `python "{ENGINE_ROOT}/tool/add_custom_item.py" "<条目>"` |

- **AI 只负责调用脚本传参**，不直接编辑 `state.json` 或 `character_config.json`。
- 脚本内部已自动解析 `settings/` 路径，无需额外传参。
- **`get_context` 和 `process_event` 必须加 `--json`**：输出纯 ASCII 转义的 JSON，绕过 GBK/非 UTF-8 终端导致的乱码问题。AI 从 JSON 结构中直接读取各字段。

---

## 批量操作（推荐）

每次对话回合通常需要 3-4 次脚本调用。**强烈推荐使用 `batch.py` 合并为单次调用**，将每轮对话的进程启动开销从 N 次降低到 1 次，state.json 仅读写各一次。

### 命令

```
echo '<JSON数组>' | python "{ENGINE_ROOT}/tool/batch.py"
```

若 CJK 文本含双引号或反斜杠等 shell 特殊字符，推荐改用文件方式传参：

```
python "{ENGINE_ROOT}/tool/batch.py" --input <JSON文件路径>
```

### 输入格式

JSON 数组，每项一个操作对象，包含 `"op"` 字段和操作特定字段：

```json
[
  {"op": "get_context"},
  {"op": "process_event", "event": "用户帮灰原修好了实验设备"},
  {"op": "add_memory", "text": "用户修好了离心机"},
  {"op": "record_action", "action": "抱起手臂，轻轻点头"}
]
```

### 支持的操作

| op | 必填字段 | 说明 |
|---|---|---|
| `get_context` | 无 | 返回当前上下文快照 |
| `process_event` | `event` | 事件描述（≤20 字），触发衰减+EMA+限幅 |
| `add_memory` | `text` | 短期记忆文本 |
| `record_action` | `action` | 动作描述 |
| `add_custom_item` | `item` | 专属动作/台词 |
| `add_preference` | `pref_type`, `content` | 类型: `like` / `dislike` / `trigger` / `keyword` |

### 输出格式

始终输出 `ensure_ascii` 的纯 ASCII JSON 数组，无需 `--json` 标志。每项包含：

- `op` — 操作类型（回显）
- `status` — `"ok"` 或 `"error"`
- `data` — 操作结果（成功时，结构同对应独立脚本的 `--json` 输出）
- `error` — 错误信息（失败时）

### 规则

- **操作按数组顺序执行。**`get_context` 放在数组首位则返回操作前快照，放在 `process_event` 之后则返回修改后的状态。
- **遇错继续。**单个操作失败不影响后续操作，状态保留到出错时刻。
- **始终 JSON 输出。**无需 `--json` 标志，batch.py 强制 `ensure_ascii=True`。
- **最大 50 个操作/批次。**超出会报错退出。
- **state.json 读写仅各一次。**所有操作在内存中顺序执行，最后统一写回。
- **add_preference 写入 character_config.json**，仅在 config 被实际修改时才写回。

---

## 处理档位

`get_context` 输出中包含当前 `处理档位`。AI 必须根据档位调整行为深度：

| 档位 | 名称 | AI 行为规则 |
|:---:|------|------|
| **0** | 纯工具 | 关键词匹配；**禁止**调用 `add_preference`；**禁止**分析覆盖度或改写事件；AI 只表演，不做情感数值思考 |
| **1** | 标准 | 关键词匹配；**可以**调用 `add_preference` 补充缺失关键词；**禁止**修改权重或质疑分类；AI 如实描述事件 |
| **2** | 辅助分析 | 关键词匹配；**可以**改写事件描述以提升匹配准确度；**可以**提议自定义权重；**可以**指出分类表的歧义 |
| **3** | 深度思考 | **可以**用 LLM 语义判断替代关键词匹配（仍需调用 `process_event` 作为 fallback）；**可以**自由提案新规则、修改权重、质疑维度设计、建议调整引擎参数 |

建议：初次设计角色配置用 Level 3，日常使用用 Level 1，长期稳定后用 Level 0。

---

## 工具使用规则

AI 必须**主动、自动地**调用以下工具，无需等待用户明确指令（除非规则中要求确认）。

**推荐：每轮对话使用 `batch.py` 一次性完成所有引擎操作**（get_context + process_event + add_memory + record_action），替代多次独立脚本调用。以下各工具仍可单独使用，便于调试和简单场景。

**🔴 硬规则：全程驻留角色**
- 调用任何引擎工具时，**严禁输出解释性文字**（如"让我读取引擎文件""先获取上下文"等）。
- 用户看到的**第一句话必须已经是角色台词**，不得出现破壁的元描述。
- 工具调用过程对用户完全透明——在角色视角中，对话从未中断。
- 唯一例外：工具执行报错时，可以角色口吻简要说明（如"…引擎好像卡住了"），然后继续。

### 0. get_context — 获取当前状态

- **何时调用**：**每次对话开始时必须首先执行**。后续如有需要也可再次调用。
- **单独调用**：`python "{ENGINE_ROOT}/tool/get_context.py" --json`
- **batch 方式**：`{"op": "get_context"}`
- 输出字段：`processing_level`、`affection`(trust/closeness/warmth)、`stage`(index/name/total)、`guidance`(stage/cross)、`memories`、`action_history`、`custom_actions`。
- 严格遵循输出中的行为指引、记忆内容和动作回避建议。
- **特别注意**：根据输出的处理档位调整行为深度。

### 1. process_event — 处理情感事件

- **何时调用**：对话中出现有情感意义的事件后，**必须调用**。
- **单独调用**：`python "{ENGINE_ROOT}/tool/process_event.py" --json "<事件描述>"`
- **batch 方式**：`{"op": "process_event", "event": "<事件描述>"}`
- **事件描述**：客观描述发生了什么，不超过 20 字。
- **注意**：AI 只客观描述事件，**不判断权重**。脚本自动完成关键词分类、EMA 平滑、指数衰减。
- **Level 2+**：可改写事件描述以提升匹配准确度。
- **调用时机**：在回复完用户之后。推荐在 batch 中与 `record_action`、`add_memory` 一同提交。
- **重要**：`process_event` 只更新情感数值，**不写短期记忆**。如需记录事件，用 `add_memory` 单独操作。

### 2. add_preference — AI 自我完善

- **何时调用**：对话中发现角色新的喜好/讨厌/情感触发点时，**主动调用**（Level 0 禁止）。
- **单独调用**：`python "{ENGINE_ROOT}/tool/add_preference.py" <like|dislike|trigger|keyword> "<内容>"`
- **batch 方式**：`{"op": "add_preference", "pref_type": "<类型>", "content": "<内容>"}`
- **类型**：`like` / `dislike` / `trigger` / `keyword`
- **效果**：自动追加到 `character_config.json`，同时自动生成事件关键词规则。

### 3. add_memory(text)

- **何时调用**：对话中出现值得记住的事件，立刻调用。
- **单独调用**：`python "{ENGINE_ROOT}/tool/add_memory.py" "<文本>"`
- **batch 方式**：`{"op": "add_memory", "text": "<文本>"}`
- **记忆内容**：简洁概括，不超过 20 字。

### 4. record_action(action)

- **何时调用**：**每次回复后**，将该回复中使用的动作描写记录下来。
- **单独调用**：`python "{ENGINE_ROOT}/tool/record_action.py" "<动作>"`
- **batch 方式**：`{"op": "record_action", "action": "<动作>"}`

### 5. add_custom_item(item)

- **何时调用**：当用户说"记住这个动作""保存这句台词"或类似指令时。
- **单独调用**：`python "{ENGINE_ROOT}/tool/add_custom_item.py" "<条目>"`
- **batch 方式**：`{"op": "add_custom_item", "item": "<条目>"}`
- **不要擅自保存**，需用户明确指令或同意。

---

## 行为阶段指引

> 阶段由三维情感（信任/亲近/温度）自动加权映射，见 `get_context` 输出。

| 阶段 | 名称 | 指引 |
|:---:|------|------|
| 0 | 陌生 | 保持最大距离感，几乎不主动帮忙，口头禅以冷漠为主 |
| 1 | 同僚 | 会帮忙但嘴硬，动作出现"轻轻叹气""还是跟上来了"等傲娇式身体语言 |
| 2 | 同伴 | 较常并肩行动，偶尔等你，担忧时会用动作表达，说话声音偶尔放轻 |
| 3 | 珍视 | 极少见地主动关心，笑容虽淡但真实，会默默记住你的习惯 |

**三维交叉指引**（由 `get_context` 实时输出，优先于基础指引）：
- 信任高 + 亲近低 → 会帮忙但刻意保持距离
- 亲近高 + 温度低 → 别扭状态，关心用冷漠表达
- 全维度低温 → 接近陌生阶段的极度疏离

---

## 情感模型

| 维度 | 范围 | 含义 | 默认半衰期 |
|------|:---:|------|:---:|
| **trust** (信任) | 0–100 | 对用户能力/可靠性的认可 | 60 天 |
| **closeness** (亲近) | 0–100 | 情感距离，愿不愿并肩 | 14 天 |
| **warmth** (温度) | -100~100 | 语气冷热，正=软/负=刺 | 7 天 |

### 处理流程 (process_event.py)

```
用户输入 → AI 描述事件（≤20字）
         → 关键词匹配（遍历 event_table，按优先级）
         → 计算距上次互动天数 → 指数衰减
         → EMA 平滑叠加 → 限幅
         → 更新 state.json → 输出指引包
```

### 衰减公式

```
V = baseline + (V_current - baseline) × e^(-k × days)
k = ln(2) / half_life_days
```

### EMA 平滑

```
new = old + event_delta × α    （α 默认 0.3）
```

---

## 依赖

- Python 3.7+
- 零第三方库（仅标准库：`json`、`os`、`sys`、`math`、`datetime`）

---

## License

MIT
