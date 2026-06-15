# AI Role-Play Emotion Engine

> A lightweight, zero-server AI role-play framework. 6 Python scripts + JSON configs = a complete emotion-tracking engine.
>
> **Core philosophy: Scripts handle the numbers, AI handles the performance.**

[中文](README.md)

---

## Features

- **3D Emotion Model**: Trust + Closeness + Warmth
- **EMA Smoothing**: Prevents single interactions from causing emotional spikes — simulates human emotional inertia
- **Exponential Decay**: Emotions naturally cool over time without interaction (independent half-life per dimension)
- **AI Self-Improvement**: AI discovers character preferences during conversation, writes config automatically
- **4 Processing Levels**: From zero-token pure-tool to deep-think mode
- **Public/Private Separation**: Engine is public, character is private — switch roles by swapping two files in `settings/`
- **Multilingual**: Engine docs in Chinese & English ([ENGINE.md](ENGINE.md) / [ENGINE_EN.md](ENGINE_EN.md))

---

## Quick Start

### 1. Prepare character config

```bash
cp settings/character_config.example.json settings/character_config.json
cp settings/character_profile.example.md settings/character_profile.md
```

Edit `character_config.json`: change `character` field, customize `event_table` keywords/weights, fill in `stage_guides`, set initial `preferences`.

Edit `character_profile.md`: fill in character identity, personality, speech style, action pool, special triggers.

### 2. Prepare CLAUDE.md

Copy `CLAUDE.example.md` → `CLAUDE.md`, set the absolute path to the engine root.

### 3. Initialize state

```bash
python tool/get_context.py
```

Script auto-creates `settings/state.json` if missing.

### 4. Start chatting

Open Claude Code. The AI will:
1. Auto-call `get_context.py` at conversation start
2. Auto-call `process_event.py` after emotionally meaningful events
3. Auto-call `add_preference.py` when discovering new preferences

---

## File Structure

```
roleplay-engine/
├── ENGINE.md              ← Engine rules (Chinese)
├── ENGINE_EN.md           ← Engine rules (English)
├── README.md              ← This file (English)
├── README_EN.md           ← Chinese README
├── CLAUDE.md              ← Role router
├── CLAUDE.example.md      ← Router template (public)
├── tool/                  ← Universal engine scripts (public, role-agnostic)
│   ├── process_event.py   ← Core: keyword match + EMA + decay
│   ├── get_context.py     ← Output current state + behavior guidance
│   ├── add_preference.py  ← AI self-improvement
│   ├── add_memory.py      ← Short-term memory management
│   ├── record_action.py   ← Action logger (anti-repetition)
│   └── add_custom_item.py ← User-saved custom actions/lines
└── settings/              ← Role-specific
    ├── character_profile.md          ← Character personality
    ├── character_config.json         ← Emotion model config
    └── state.json                    ← Runtime state
```

---

## Integrating into Any Project

1. Copy `tool/` + `settings/` + `ENGINE.md` + `ENGINE_EN.md` to any directory, e.g. `D:\engines\roleplay\`
2. In the target project's `CLAUDE.md`, add:

```markdown
## Role-Play Engine

Engine root: D:\engines\roleplay

Read in order:
1. {ENGINE_ROOT}\ENGINE.md — Tool rules & engine docs
2. {ENGINE_ROOT}\settings\character_profile.md — Character personality
```

3. Copy and customize the example files in `settings/`
4. Done. The AI resolves tool paths from ENGINE.md using the declared engine root.

## Switching Roles

1. Replace `settings/character_config.json` with new role's emotion model config
2. Replace `settings/character_profile.md` with new role's personality
3. Delete or reset `settings/state.json`
4. Engine scripts (`tool/`) — **zero changes needed**

---

## Emotion Model

| Dimension | Range | Meaning | Default Half-Life |
|-----------|:-----:|---------|:-----------------:|
| **trust** | 0–100 | Trust in user's competence/reliability | 60 days |
| **closeness** | 0–100 | Emotional distance, willingness to accompany | 14 days |
| **warmth** | -100–100 | Tone warmth: positive=soft / negative=sharp | 7 days |

3D weighted mapping → 4 stages (stage names and guidance customizable in `character_config.json`).

## Processing Levels

Set `processing_level` in `character_config.json` (0–3):

| Level | Tokens | AI Behavior |
|:---:|:---:|------|
| **0** | Zero | Pure tool: AI only performs |
| **1** | Low | Standard: AI may add missing keywords |
| **2** | Mid | Assisted: AI may rewrite events, propose weights |
| **3** | High | Deep: AI freely analyzes semantics, questions rules |

## Dependencies

- Python 3.7+
- Zero third-party libraries

## License

MIT
