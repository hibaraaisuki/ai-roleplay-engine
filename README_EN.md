# AI Role-Play Emotion Engine

> A lightweight, zero-server AI role-play framework. 7 Python scripts + JSON configs = a complete emotion-tracking engine.
>
> **Core philosophy: Scripts handle the numbers, AI handles the performance.**
>
> Runs inside Claude Code and other AI coding assistants — the AI reads ENGINE.md for operational rules, calls Python scripts via CLI, and reads/writes local JSON files. The engine itself requires no server, no API key, and no network dependency.

[中文](README.md)

---

## What This Is

An emotion-tracking engine purpose-built for AI role-play. It quantifies the character-user relationship with three numerical dimensions (trust, closeness, warmth), auto-updates values via keyword matching, and drives the AI to exhibit different behavior patterns at different relationship stages.

**You don't write prompts. The engine drives them.**

---

## Features

- **3D Emotion Model**: Trust + Closeness + Warmth, weighted-mapped to 4 stages
- **EMA Smoothing**: Prevents single interactions from causing emotional spikes — simulates human emotional inertia
- **Exponential Decay**: Emotions naturally cool over time without interaction (independent half-life per dimension)
- **Batch Operations**: `batch.py` merges multiple script calls per turn into one — state.json read/written only once
- **AI Self-Improvement**: AI discovers character preferences during conversation, writes config automatically
- **4 Processing Levels**: From zero-token pure-tool to deep-think mode
- **Public/Private Separation**: Engine is public, character is private — switch roles by swapping two files in `settings/`
- **Multilingual**: Engine docs + README in Chinese & English

---

## How to Use

### 1. Prepare Character Config

Create `settings/character_config.json` (emotion model) and `settings/character_profile.md` (character personality). Copy from an existing character config or write from scratch — see [ENGINE.md](ENGINE.md) for processing level guidance.

`character_config.json` core fields:
- `character` — role name
- `dimensions` — 3D emotion parameters (baselines, half-lives, ranges)
- `event_table` — keyword → delta mapping rules
- `stage_guides` — behavior guidance text for each relationship stage
- `processing_level` — processing tier (0-3)

`character_profile.md` — character identity, personality, speech style, action pool, special triggers.

### 2. Prepare CLAUDE.md

Declare the engine path in your project's `CLAUDE.md`:

```markdown
Engine root: C:\Users\Administrator\Documents\AI助手记忆

Read in order:
1. {ENGINE_ROOT}\ENGINE.md — Tool rules
2. {ENGINE_ROOT}\settings\character_profile.md — Character personality
```

### 3. Initialize State

```bash
python tool/get_context.py
```

The script auto-creates `settings/state.json` if missing.

### 4. Start Chatting

The AI will:
1. Auto-fetch emotional context at conversation start
2. Auto-process emotional events, record memories and actions
3. Auto-write new preferences to config when discovered
4. Auto-adjust tone and behavior based on current stage

---

## File Structure

```
roleplay-engine/
├── ENGINE.md              ← AI operations manual (Chinese)
├── ENGINE_EN.md           ← AI operations manual (English)
├── README.md              ← Chinese README
├── README_EN.md           ← This file (English)
├── CLAUDE.md              ← Role router (points to engine directory)
├── tool/                  ← Universal engine scripts (public, role-agnostic)
│   ├── batch.py           ← Batch ops (recommended)
│   ├── process_event.py   ← Core: keyword match + EMA + decay
│   ├── get_context.py     ← Output current state + behavior guidance
│   ├── add_preference.py  ← AI self-improvement: append preferences
│   ├── add_memory.py      ← Short-term memory management
│   ├── record_action.py   ← Action logger (anti-repetition)
│   └── add_custom_item.py ← User-saved custom actions/lines
└── settings/              ← Role-specific (private)
    ├── character_profile.md   ← Character personality & speech
    ├── character_config.json  ← Emotion model config
    └── state.json             ← Runtime state
```

---

## How It Works

### 3D Emotion Model

| Dimension | Range | Meaning | Default Half-Life |
|-----------|:-----:|---------|:-----------------:|
| **trust** | 0–100 | Trust in user's competence/reliability | 60 days |
| **closeness** | 0–100 | Emotional distance, willingness to accompany | 14 days |
| **warmth** | -100–100 | Tone warmth: positive=soft / negative=sharp | 7 days |

Three dimensions are weighted-mapped to four relationship stages (Stranger → Colleague → Companion → Cherished). Stage names and guidance are customizable in `character_config.json`.

### Processing Pipeline

```
User input → AI describes event (≤20 chars)
           → Keyword match (iterate event_table, first-match priority)
           → Calculate days since last interaction → Exponential decay
           → EMA smoothing → Clamp to valid range
           → Update state.json → Output stage + behavior guidance
```

### Decay Formula

Without interaction, emotions naturally regress toward baseline:

```
V = baseline + (V_current - baseline) × e^(-k × days)
k = ln(2) / half_life_days
```

- trust has the longest half-life (60 days) — trust is slow to earn and slow to lose
- warmth has the shortest (7 days) — tone fluctuates fastest

### EMA Smoothing

Prevents single events from causing wild value swings:

```
new = old + event_delta × α    (α default: 0.3)
```

Event deltas don't apply directly at full magnitude — they accumulate gradually through the smoothing coefficient, simulating emotional inertia.

---

## Live Demo

Using the "Mouri Ran" character — watch how the engine drives emotional change across a few conversation turns.

> Start: trust 55 / closeness 40 / warmth 30 — **First Meeting** stage

```
User: "Hi! I just moved in next door. Nice to meet you～"

Event: First-time greeting
Match: Daily interaction → trust+0, closeness+0.35, warmth+0.35  (×α=0.35)
─────────────────────────────────────────────────
trust 55 → 55    closeness 40 → 40    warmth 30 → 30
Stage: First Meeting — "Polite but keeps distance, uses formal speech, smile is courteous and restrained"

Ran: (bows slightly, with a courteous, restrained smile)
     "Hello, I'm Mouri Ran. Nice to meet you. Let me know if you ever need anything."
```

```
User: "I heard you're amazing at making bento? I tried making one today — here, try it."

Event: User shares homemade food with Ran
Match: Cooking / sharing food → trust+0, closeness+1.05, warmth+1.4  (×α=0.35)
─────────────────────────────────────────────────
trust 56 → 56    closeness 43 → 44    warmth 33 → 34
Stage: Friend — "Relaxed natural tone, chats about daily life, genuine smile"

Ran: (eyes light up, accepting the bento box with both hands)
     "Wow～ it smells amazing! You're pretty good at this. I'll make one for you next time — my treat!"
```

```
User: "Don't worry. I'll protect you. No one's going to hurt you."

Event: User firmly promises to protect Ran
Match: Being protected → trust+0.7, closeness+2.1, warmth+1.75  (×α=0.35)
─────────────────────────────────────────────────
trust 57 → 58    closeness 46 → 48    warmth 35 → 37
Stage: Good Friend — "Actively invites to meals or outings, prepares bento for them, care shows openly"

Ran: (blushes slightly, then breaks into a warm smile)
     "Thank you... I'm really lucky to have met you. Hey, are you free this weekend? Let's go to the fireworks festival together — I'll make bento for us."
```

> From a polite smile to sharing bento to standing side by side — **same engine, three keyword matches, three completely different versions of Ran.**

---


Set `processing_level` in `character_config.json` (0-3) to control AI analysis depth:

| Level | Tokens | AI Behavior |
|:---:|:---:|------|
| **0** | Zero | Pure tool: AI only performs, no analysis |
| **1** | Low | Standard: AI may add missing keywords |
| **2** | Mid | Assisted: AI may rewrite events, propose weights |
| **3** | High | Deep: AI freely analyzes semantics, questions rules |

Suggested: Level 3 for initial config design, Level 1 for daily use, Level 0 for stable operation.

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

3. Prepare character config files in `settings/`
4. Done. The AI resolves tool paths from ENGINE.md using the declared engine root.

## Switching Roles

1. Replace `settings/character_config.json` with new role's emotion model config
2. Replace `settings/character_profile.md` with new role's personality
3. Delete or reset `settings/state.json`
4. Engine scripts (`tool/`) — **zero changes needed**

---

## Dependencies

- Python 3.7+
- Zero third-party libraries (standard library only: `json`, `os`, `sys`, `math`, `datetime`)

## License

MIT
