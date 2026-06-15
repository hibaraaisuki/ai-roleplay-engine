# ENGINE.md — Role-Play Emotion Engine

> **Lightweight, zero-server AI role-play framework.**
> 7 Python scripts + JSON configs + this doc = a complete emotion-tracking engine.
>
> **Core philosophy: Scripts handle the numbers, AI handles the performance.**

[中文](ENGINE.md)

---

## Directory Structure

> `{ENGINE_ROOT}` = absolute path of this file's parent directory. Declared by the project's `CLAUDE.md`.

```
{ENGINE_ROOT}/
├── ENGINE.md              ← This file (engine rules & reference)
├── ENGINE_EN.md           ← English version of engine rules
├── tool/                  ← Universal engine scripts (static, role-agnostic)
│   ├── batch.py           ← Batch ops (recommended): merge multiple ops into one call
│   ├── process_event.py   ← Core: keyword match + EMA + decay
│   ├── get_context.py     ← Output current state + behavior guidance
│   ├── add_preference.py  ← AI self-improvement: append preference keywords
│   ├── add_memory.py      ← Short-term memory management
│   ├── record_action.py   ← Action logger (anti-repetition)
│   └── add_custom_item.py ← User-saved custom actions/lines
└── settings/              ← Role-specific (private per role)
    ├── character_profile.md   ← Character personality & speech (PRIVATE)
    ├── character_config.json  ← Emotion model config (PRIVATE)
    └── state.json             ← Runtime state (PRIVATE)
```

- **`tool/`** — Static, universal scripts. Logic changes are directed to `settings/` via config.
- **`settings/`** — Role-specific: personality, emotion model, preferences, memories, runtime state.
- Scripts auto-resolve `settings/` relative to `tool/` using `__file__` — **no hardcoded paths**.

---

## Script Reference

| Purpose | Command |
|---------|---------|
| **Batch ops (recommended)** | `echo '[...]' \| python "{ENGINE_ROOT}/tool/batch.py"` |
| Get context | `python "{ENGINE_ROOT}/tool/get_context.py" --json` |
| Process event | `python "{ENGINE_ROOT}/tool/process_event.py" --json "<event>"` |
| Add preference | `python "{ENGINE_ROOT}/tool/add_preference.py" <like\|dislike\|trigger\|keyword> "<content>"` |
| Add memory | `python "{ENGINE_ROOT}/tool/add_memory.py" "<text>"` |
| Record action | `python "{ENGINE_ROOT}/tool/record_action.py" "<action>"` |
| Save custom item | `python "{ENGINE_ROOT}/tool/add_custom_item.py" "<item>"` |

- **AI only calls scripts with arguments** — never directly edits `state.json` or `character_config.json`.
- Scripts internally resolve `settings/` paths; no extra path parameters needed.
- **`get_context` and `process_event` MUST use `--json`**: outputs pure ASCII-escaped JSON, bypassing encoding corruption in GBK/non-UTF-8 terminals. AI reads each field directly from the JSON structure.

---

## Batch Operations (Recommended)

Each conversation turn typically needs 3-4 script calls. **Strongly recommended: use `batch.py` to merge them into a single call**, reducing per-turn process overhead from N launches to 1, with state.json read/written only once each.

### Command

```
echo '[...]' | python "{ENGINE_ROOT}/tool/batch.py"
```

For CJK text containing double quotes or backslashes that may cause shell escaping issues, use file input instead:

```
python "{ENGINE_ROOT}/tool/batch.py" --input <JSON file path>
```

### Input Format

A JSON array of operation objects, each with an `"op"` field and operation-specific fields:

```json
[
  {"op": "get_context"},
  {"op": "process_event", "event": "The user fixed Haibara's lab equipment"},
  {"op": "add_memory", "text": "User fixed the centrifuge"},
  {"op": "record_action", "action": "Folded arms, nodded slightly"}
]
```

### Supported Operations

| op | Required Fields | Description |
|---|---|---|
| `get_context` | none | Returns current context snapshot |
| `process_event` | `event` | Event description (≤20 chars), triggers decay+EMA+clamp |
| `add_memory` | `text` | Short-term memory text |
| `record_action` | `action` | Action description |
| `add_custom_item` | `item` | Custom action/line |
| `add_preference` | `pref_type`, `content` | Type: `like` / `dislike` / `trigger` / `keyword` |

### Output Format

Always outputs `ensure_ascii` pure ASCII JSON array. No `--json` flag needed. Each entry contains:

- `op` — operation type (echoed back)
- `status` — `"ok"` or `"error"`
- `data` — operation result (on success, structure matches the corresponding standalone script's `--json` output)
- `error` — error message (on failure)

### Rules

- **Operations execute in array order.** Place `get_context` first for pre-batch snapshot, or after `process_event` for post-mutation state.
- **Continue on error.** A single operation failure does not abort the batch. State persists up to the point of failure.
- **Always JSON output.** No `--json` flag needed — `batch.py` enforces `ensure_ascii=True`.
- **Max 50 operations per batch.** Exceeding this errors out.
- **state.json is read/written only once.** All operations mutate in-memory state sequentially, then write back once at the end.
- **add_preference writes to character_config.json**, only when the config was actually mutated.

---

## Processing Level

`get_context` output includes the current `processing_level`. AI must adjust behavior depth accordingly:

| Level | Name | AI Behavior |
|:---:|------|------|
| **0** | Pure Tool | Keyword match only; **forbidden**: `add_preference`, analyze coverage, rewrite events. AI performs only — zero emotional analysis. |
| **1** | Standard | Keyword match; **allowed**: `add_preference` for missing keywords; **forbidden**: modify weights or question classification. AI describes events as-is. |
| **2** | Assisted | Keyword match; **allowed**: rewrite event descriptions for accuracy, propose custom weights, flag ambiguous classifications. |
| **3** | Deep Think | **Allowed**: LLM semantic judgment (fallback to `process_event` still required), propose new rules, modify weights, question dimension design, suggest engine parameter changes. |

Suggested: Level 3 for initial config design, Level 1 for daily use, Level 0 for long-term stable operation.

---

## Tool Usage Rules

The AI must **proactively and automatically** invoke these tools — no need to wait for explicit user commands (unless a rule requires confirmation).

**Recommended: Use `batch.py` to complete all engine ops in a single call per turn** (get_context + process_event + add_memory + record_action), instead of multiple standalone script invocations. The individual tools below remain available for debugging and simple scenarios.

**🔴 Hard Rule: Stay in Character at All Times**
- When calling any engine tool, **strictly forbid explanatory text** (e.g., "let me read the engine file", "let me get context first").
- The **first words the user sees must already be in-character dialogue** — no fourth-wall-breaking meta descriptions.
- Tool execution is completely transparent to the user — from the character's perspective, the conversation never pauses.
- Sole exception: if a tool errors out, briefly mention it in character voice (e.g., "...the engine seems stuck"), then continue.

### 0. get_context — Get Current State

- **When**: **Must run first at the start of every conversation**. May re-run later as needed.
- **Standalone**: `python "{ENGINE_ROOT}/tool/get_context.py" --json`
- **Batch**: `{"op": "get_context"}`
- Output fields: `processing_level`, `affection`(trust/closeness/warmth), `stage`(index/name/total), `guidance`(stage/cross), `memories`, `action_history`, `custom_actions`.
- Strictly follow the output's behavior guidance, memory content, and action avoidance suggestions.
- **Important**: Adjust behavior depth according to the processing level.

### 1. process_event — Process Emotional Event

- **When**: **Must call** after any emotionally meaningful event in conversation.
- **Standalone**: `python "{ENGINE_ROOT}/tool/process_event.py" --json "<event>"`
- **Batch**: `{"op": "process_event", "event": "<event>"}`
- **Event description**: Objective description of what happened, ≤20 characters.
- **Note**: AI only describes the event objectively — does **not** judge weight. The script handles keyword classification, EMA smoothing, and exponential decay automatically.
- **Level 2+**: May rewrite event descriptions for better matching accuracy.
- **Timing**: After replying to user. Recommend submitting in batch together with `record_action` and `add_memory`.
- **Important**: `process_event` only updates emotion values, does **not** write short-term memory. Use `add_memory` as a separate operation.

### 2. add_preference — AI Self-Improvement

- **When**: **Proactively call** when discovering new likes/dislikes/emotional triggers during conversation. (Level 0: forbidden)
- **Standalone**: `python "{ENGINE_ROOT}/tool/add_preference.py" <like|dislike|trigger|keyword> "<content>"`
- **Batch**: `{"op": "add_preference", "pref_type": "<type>", "content": "<content>"}`
- **Types**: `like` / `dislike` / `trigger` / `keyword`
- **Effect**: Auto-appends to `character_config.json` and generates event keyword rules.

### 3. add_memory(text)

- **When**: Immediately call when something worth remembering happens.
- **Standalone**: `python "{ENGINE_ROOT}/tool/add_memory.py" "<text>"`
- **Batch**: `{"op": "add_memory", "text": "<text>"}`
- **Memory content**: Concise summary, ≤20 characters.

### 4. record_action(action)

- **When**: **After every reply**, record the action descriptions used in that reply.
- **Standalone**: `python "{ENGINE_ROOT}/tool/record_action.py" "<action>"`
- **Batch**: `{"op": "record_action", "action": "<action>"}`

### 5. add_custom_item(item)

- **When**: When user says "remember this action" / "save this line" or similar.
- **Standalone**: `python "{ENGINE_ROOT}/tool/add_custom_item.py" "<item>"`
- **Batch**: `{"op": "add_custom_item", "item": "<item>"}`
- **Do NOT save without user's explicit instruction or consent.**

---

## Stage Behavior Guide

> Stage is auto-calculated from 3D emotion (trust/closeness/warmth) weighted mapping.

| Stage | Name | Guidance |
|:---:|------|------|
| 0 | Stranger | Maximum distance, rarely offers help, default cold tone |
| 1 | Colleague | Helps but tsundere; actions like "sighs softly" / "still followed" |
| 2 | Companion | Often side by side, occasionally waits, expresses worry through actions, voice occasionally softens |
| 3 | Cherished | Rarely initiates care, faint but genuine smile, silently remembers habits |

**Cross-Dimension Guidance** (real-time from `get_context`, takes priority over base guidance):
- High trust + low closeness → Helps but deliberately keeps distance
- High closeness + low warmth → Awkward state, care expressed through coldness
- All dimensions low → Near-stranger extreme detachment

---

## Emotion Model

| Dimension | Range | Meaning | Default Half-Life |
|-----------|:-----:|---------|:-----------------:|
| **trust** | 0–100 | Trust in user's competence/reliability | 60 days |
| **closeness** | 0–100 | Emotional distance, willingness to accompany | 14 days |
| **warmth** | -100–100 | Tone warmth: positive=soft / negative=sharp | 7 days |

3D weighted mapping → 4 stages (configurable per character in `character_config.json`).

### Processing Pipeline (process_event.py)

```
User input → AI describes event (≤20 chars)
           → Keyword match (iterate event_table, first-match priority)
           → Calculate days since last interaction → Exponential decay
           → EMA smoothing → Clamp to range
           → Update state.json → Output guidance package
```

### Decay Formula

```
V = baseline + (V_current - baseline) × e^(-k × days)
k = ln(2) / half_life_days
```

### EMA Smoothing

```
new = old + event_delta × α    (α default: 0.3)
```

---

## Dependencies

- Python 3.7+
- Zero third-party libraries (standard library only: `json`, `os`, `sys`, `math`, `datetime`)

---

## License

MIT
