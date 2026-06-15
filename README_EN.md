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

If you have already deployed `Claude` and are using it for many tasks, why not make its interactions more engaging? All you need to do is download a few files and add the invocation instructions on `CLAUDE.md`. By consuming a small amount of tokens, you can cultivate an emotionally rich AI assistant.

**You don't write prompts. The engine drives them.**

---

## Features

- **3D Emotion Model**: Trust + Closeness + Warmth, weighted-mapped to 4 stages
- **EMA Smoothing**: Prevents single interactions from causing emotional spikes — simulates human emotional inertia
- **Exponential Decay**: Emotions naturally cool over time without interaction (independent half-life per dimension)
- **Batch Operations**: `batch.py` merges multiple script calls per turn into one — state.json read/written only once
- **AI Self-Improvement**: AI discovers character preferences during conversation, writes config automatically
- **Two-Tier Memory**: Core permanent memory + recent sliding memory with importance-based eviction
- **4 Processing Levels**: From zero-token pure-tool to deep-think mode
- **Public/Private Separation**: Engine is public, character is private — switch roles by swapping two files in `settings/`
- **Multilingual**: Engine docs + README in Chinese & English

---

## How to Use

### Step 1: Download Engine Files

Copy these files/folders to the directory where you want to keep the engine (e.g., `D:\engines\roleplay\`):

```
tool/                  ← All 7 Python scripts (required)
ENGINE.md              ← AI operations manual (Chinese)
ENGINE_EN.md           ← AI operations manual (English)
settings/              ← Character config directory (see Step 2)
```

You don't need to copy `README.md` or `CLAUDE.md` — README is for human reference, and CLAUDE.md goes in your own project (Step 4).

### Step 2: Choose Language & Rename Settings

`settings/` includes pre-written configs in Chinese and English. Pick one and remove the suffix:

| Desired language | Action |
|------------------|--------|
| 中文 | `character_config_zh.json` → rename to `character_config.json` |
| | `character_profile_zh.md` → rename to `character_profile.md` |
| English | `character_config_en.json` → rename to `character_config.json` |
| | `character_profile_en.md` → rename to `character_profile.md` |

> The engine only recognizes the exact filenames `character_config.json` and `character_profile.md`. You must rename — don't modify the filename references in the engine source. Extra language files (e.g., `_zh.json`) can be kept or deleted, the engine ignores them.

### Step 3: Verify Directory Structure

After renaming, your engine directory should look like this:

```
D:\engines\roleplay\
├── ENGINE.md              ← AI operations manual (Chinese)
├── ENGINE_EN.md           ← AI operations manual (English)
├── tool/                  ← Engine scripts
│   ├── batch.py
│   ├── process_event.py
│   ├── get_context.py
│   ├── add_preference.py
│   ├── add_memory.py
│   ├── record_action.py
│   └── add_custom_item.py
└── settings/
    ├── character_profile.md   ← Character personality (renamed)
    ├── character_config.json  ← Emotion model (renamed)
    └── state.json             ← Auto-generated — no need to create manually
```

### Step 4: Configure CLAUDE.md

In **your own project's root directory**, create or edit `CLAUDE.md` and add:

```markdown
## Role-Play Engine

Engine root: D:\engines\roleplay

Read in this order to enable role-play functionality:
1. {ENGINE_ROOT}\ENGINE.md — Tool usage rules, processing levels, stage behavior guide
2. {ENGINE_ROOT}\settings\character_profile.md — Character personality, speech patterns, mannerisms

All script paths are relative to the engine root. ENGINE.md contains the full script reference table.
```

> **Use your own absolute path**, e.g., `C:\Users\YourName\Documents\roleplay`. If using English docs, change the first line to `ENGINE_EN.md`.

### Step 5: Initialize and Start

```bash
python tool/get_context.py
```

The script auto-creates `settings/state.json`. Then just start chatting — the AI will automatically fetch context, process events, record memories and actions.

---

## Customizing Character Settings

The pre-written Haibara Ai config works out of the box, or you can adapt it for your own character.

### Editing the Emotion Model (character_config.json)

| Field | Purpose | How to Edit |
|-------|---------|-------------|
| `dimensions` | 3D emotion baselines, half-lives, ranges | Adjust values; longer trust half-life = slower to gain/lose |
| `event_table` | Keyword → emotion delta rules | Write trigger words and delta values for your character |
| `stages` | Four stage names | Rename to fit your character's relationship arc |
| `stage_guides` | Behavior guidance per stage | Tell the AI how to act at each stage |
| `processing_level` | Processing depth (0-3) | Use 3 for initial tuning, 1 for daily use, 0 when stable |

### Editing Character Personality (character_profile.md)

Follow the template format: identity, personality, speech style, action pool, special triggers. Use the preset file as a reference for structure.

### Switching Roles

1. Replace `settings/character_config.json` with the new role
2. Replace `settings/character_profile.md` with the new role
3. Delete `settings/state.json` (reset emotional state)
4. Engine scripts (`tool/`) — **zero changes needed**

---

## Switching Languages

1. Rename the target language setting files (e.g., `character_config_en.json` → `character_config.json`)
2. Do the same for `character_profile_*.md` → `character_profile.md`
3. Delete `state.json` (old memories can't migrate between languages)
4. Update `CLAUDE.md` to point to `ENGINE_EN.md` instead of `ENGINE.md` (or vice versa)

> **Note**: `character_config.json` and `character_profile.md` are hardcoded filenames — the engine only reads these exact names. Do not edit the source code to change them. `state.json` contains runtime data (memories, action history) which cannot be migrated between languages — a reset is required.

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

## Dependencies

- Python 3.7+
- Zero third-party libraries (standard library only: `json`, `os`, `sys`, `math`, `datetime`)

## License

MIT
