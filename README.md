# AI 角色扮演情感引擎

> 轻量级、零服务器的 AI 角色扮演框架。6 个 Python 脚本 + JSON 配置 = 完整的情感追踪引擎。
>
> **核心理念：工具管数值，AI 只管演。**

[English](README_EN.md)

---

## 特性

- **三维情感模型**：信任度 (trust) + 亲近度 (closeness) + 温度 (warmth)
- **EMA 平滑**：防止单次互动造成情感剧烈跳变，模拟人类"慢热慢冷"的惯性
- **指数衰减**：长时间不互动，情感自然降温（三维各自独立的半衰期）
- **AI 自我完善**：对话中自动发现角色偏好，写入配置，无需手动编辑 JSON
- **四档处理深度**：从零 token 纯工具到深度思考，按需切换
- **公私分离**：引擎公开，角色私有——切换角色只需替换 `settings/` 下的两个 `character_*` 文件
- **多语言**：引擎文档提供中英双版 ([ENGINE.md](ENGINE.md) / [ENGINE_EN.md](ENGINE_EN.md))

---

## 快速开始

### 1. 准备角色配置

```bash
cp settings/character_config.example.json settings/character_config.json
cp settings/character_profile.example.md settings/character_profile.md
```

编辑 `character_config.json`：修改 `character` 字段、`event_table` 关键词与权重、`stage_guides` 行为指引、初始 `preferences`。

编辑 `character_profile.md`：填入角色的身份、性格、说话风格、动作池、特殊触发等。

### 2. 准备 CLAUDE.md

复制 `CLAUDE.example.md` → `CLAUDE.md`，设置引擎根目录的绝对路径。

### 3. 初始化状态

```bash
python tool/get_context.py
```

脚本会自动创建 `settings/state.json`（如不存在）。

### 4. 开始对话

打开 Claude Code，AI 会：
1. 对话开始自动调用 `get_context.py` 获取情感状态
2. 对话中自动调用 `process_event.py` 处理情感事件
3. 发现新偏好时自动调用 `add_preference.py` 写入配置

---

## 文件结构

```
roleplay-engine/
├── ENGINE.md              ← 引擎规则说明书（中文）
├── ENGINE_EN.md           ← Engine rules (English)
├── README.md              ← 本文件（中文）
├── README_EN.md           ← English README
├── CLAUDE.md              ← 角色路由
├── CLAUDE.example.md      ← 路由模板（公开）
├── tool/                  ← 通用引擎脚本（公开，与角色无关）
│   ├── process_event.py   ← 核心：关键词分类 + EMA + 衰减
│   ├── get_context.py     ← 输出当前状态 + 行为指引
│   ├── add_preference.py  ← AI 自我完善
│   ├── add_memory.py      ← 短期记忆管理
│   ├── record_action.py   ← 动作记录（防重复）
│   └── add_custom_item.py ← 用户专属动作/台词
└── settings/              ← 角色专属
    ├── character_profile.md          ← 角色人格
    ├── character_config.json         ← 情感模型配置
    ├── state.json                    ← 运行时状态
```

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

3. 复制并自定义 `settings/` 下的 example 文件
4. 完成。AI 会根据 ENGINE.md 自动解析并调用工具

## 切换角色

1. 替换 `settings/character_config.json` 为新角色的情感模型配置
2. 替换 `settings/character_profile.md` 为新角色的人格描述
3. 删除或重置 `settings/state.json`
4. 引擎脚本（`tool/`）——**一行不动**

---

## 情感模型

| 维度 | 范围 | 含义 | 默认半衰期 |
|------|:---:|------|:---:|
| **trust** (信任) | 0–100 | 对用户能力/可靠性的认可 | 60 天 |
| **closeness** (亲近) | 0–100 | 情感距离，愿不愿并肩 | 14 天 |
| **warmth** (温度) | -100~100 | 语气冷热，正=软/负=刺 | 7 天 |

三维加权映射到四阶段（阶段名称和各阶段指引可在 `character_config.json` 中自定义）。

## 处理档位

在 `character_config.json` 中设置 `processing_level` (0-3)：

| 档位 | Token | AI 行为 |
|:---:|:---:|------|
| **0** | 零 | 纯工具：AI 不分析不提议 |
| **1** | 低 | 标准：AI 可补充缺失关键词 |
| **2** | 中 | 辅助：AI 可改写事件、提议权重 |
| **3** | 高 | 深度：AI 自由分析语义、质疑规则 |

## 依赖

- Python 3.7+
- 零第三方库

## License

MIT
