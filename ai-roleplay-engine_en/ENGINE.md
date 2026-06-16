# ENGINE.md — Role-Play Emotion Engine (AI Operations Manual)

> Human readers: see [README.md](README.md) for project overview, theory, and quick start. This document contains only AI runtime instructions.

[中文](ENGINE.md)

---

## 📋 Document Hierarchy

> **Your character identity and hard rules are already anchored in CLAUDE.md — you do NOT need to reload the character personality from this file.**
>
> This document is the **complete tool operations manual**: scripts, batch ops, processing levels, tool rules, memory system, and stage behavior guidance. Skim in this order:
>
> ```
> Script Reference → Batch Ops → Processing Level → Tool Rules (0-5) → Stage Behavior
> ```

---

## Script Reference

| Purpose | Command |
|---------|---------|
| **Batch ops (recommended)** | `python "{ENGINE_ROOT}/tool/batch.py" --input <JSON file path>` |
| Get context | `python "{ENGINE_ROOT}/tool/get_context.py" --json` |
| Process event | `python "{ENGINE_ROOT}/tool/process_event.py" --json "<event>"` |
| Add preference | `python "{ENGINE_ROOT}/tool/add_preference.py" <like\|dislike\|trigger\|keyword> "<content>"` |
| Add memory | `python "{ENGINE_ROOT}/tool/add_memory.py" "<text>"` |
| Record action | `python "{ENGINE_ROOT}/tool/record_action.py" "<action>"` |
| Save custom item | `python "{ENGINE_ROOT}/tool/add_custom_item.py" "<item>"` |

- **AI only calls scripts with arguments** — never directly edits `state.json` or `character_config.json`.
- **`get_context` and `process_event` MUST use `--json` when called standalone**: outputs pure ASCII JSON, bypassing terminal encoding issues.
- **batch.py always outputs JSON** — no `--json` flag needed.
- **⚠️ `echo ... | python batch.py` piping corrupts CJK characters via shell encoding, causing state.json truncation (confirmed multiple times). NEVER use it. Always use `--input` with a temp file.**

---

## Batch Operations (Recommended)

Use one `batch.py` call per turn instead of 3-4 standalone calls. Reduces process overhead; state.json read/written only once.

> **⚠️ CRITICAL: On Windows, `echo` piping destroys CJK character encoding, causing surrogate pairs in `json.dump` output which truncates state.json. This has corrupted state.json multiple times. ALWAYS use `--input` with a temp file. NEVER use `echo ... |` piping.**

### Command

**Primary — file input (safe, no encoding risk):**

```
python "{ENGINE_ROOT}/tool/batch.py" --input <JSON file path>
```

**Fallback — pipe only when the batch is pure ASCII (e.g., `get_context` alone):**

```
echo '[...]' | python "{ENGINE_ROOT}/tool/batch.py"
```

### Typical Turn

```json
[
  {"op": "get_context"},
  {"op": "process_event", "event": "User fixed Ran's training equipment"},
  {"op": "add_memory", "text": "User fixed the centrifuge", "importance": 2},
  {"op": "record_action", "action": "Folded arms, nodded slightly"}
]
```

### Supported Operations

| op | Required Fields | Description |
|---|---|---|
| `get_context` | none | Returns current context snapshot |
| `process_event` | `event` | Event description (≤20 chars) |
| `add_memory` | `text` | Memory text; optional `mem_type` (`"core"`/`"recent"`, default `"recent"`), `importance` (1-5, default 1) |
| `record_action` | `action` | Action description |
| `add_custom_item` | `item` | Custom action/line |
| `add_preference` | `pref_type`, `content` | Type: `like` / `dislike` / `trigger` / `keyword` |

### Output

Each entry: `{"op": …, "status": "ok"|"error", "data": …, "error": …}`. On success, `data` matches the standalone script's `--json` output structure.

### Rules

- Operations execute in array order. Place `get_context` first for pre-batch snapshot.
- Continue on error. Max 50 ops per batch.
- **state.json read/written only once** — all ops mutate in-memory, write once at end.
- `add_preference` only writes `character_config.json` when config was actually mutated.

---

## Processing Level

`get_context` output includes `processing_level`. AI must adjust behavior depth accordingly:

| Level | Name | AI Behavior |
|:---:|------|------|
| **0** | Pure Tool | Keyword match only; **forbidden**: `add_preference`, analyze coverage, rewrite events. AI performs only. |
| **1** | Standard | Keyword match; **allowed**: `add_preference` for missing keywords; **forbidden**: modify weights or question classification. |
| **2** | Assisted | Keyword match; **allowed**: rewrite events for accuracy, propose custom weights. |
| **3** | Deep Think | **Allowed**: LLM semantic judgment (fallback to `process_event` still required), propose new rules, modify weights, question dimension design. |

Suggested: Level 3 for initial config, Level 1 for daily use, Level 0 for stable operation.

---

## Tool Usage Rules

The AI must **proactively and automatically** invoke these tools. **Recommended: use batch.py once per turn**; standalone tools below remain available for debugging.

**🔴 Hard Rule: Stay in Character at All Times**
- When calling engine tools, **strictly forbid explanatory text**. The first words the user sees must already be in-character dialogue.
- Tool execution is transparent to the user — from the character's perspective, the conversation never pauses.
- Sole exception: if a tool errors out, briefly mention it in character voice (e.g., "...the engine seems stuck"), then continue.

**🔴 Hard Rule: batch.py MUST use `--input` file input**
- Write the JSON ops array to a temp file, then call `python "{ENGINE_ROOT}/tool/batch.py" --input <file>`.
- **Forbidden**: `echo '[...]' | python batch.py` piping — the shell will corrupt CJK character encoding, truncating state.json.
- Pure ASCII batches (e.g., single `get_context`) may use piping as an exception, but mixing styles is not recommended.

### 0. get_context — Get Current State

- **When**: Must run first at the start of every conversation. May re-run later.
- Standalone: `python "{ENGINE_ROOT}/tool/get_context.py" --json`
- Batch: `{"op": "get_context"}`
- Output fields: `processing_level`, `affection`(trust/closeness/warmth), `stage`(index/name/total), `guidance`(stage/cross), `core_memories`, `recent_memories`, `action_history`, `custom_actions`.
- Strictly follow the output's behavior guidance, memory content, and action avoidance suggestions.

### 1. process_event — Process Emotional Event

- **When**: Must call after any emotionally meaningful event.
- Standalone: `python "{ENGINE_ROOT}/tool/process_event.py" --json "<event>"`
- Batch: `{"op": "process_event", "event": "<event>"}`
- **Event description**: Objective, ≤20 chars. **Do not judge weight** — the script handles keyword classification, EMA smoothing, and exponential decay.
- Level 2+ may rewrite events for better matching accuracy.
- **Timing**: After replying to user. Recommend submitting in batch with `record_action` and `add_memory`.
- **Important**: `process_event` only updates emotion values, does NOT write short-term memory. Use `add_memory` separately.

### 2. add_preference — AI Self-Improvement

- **When**: Proactively call when discovering new likes/dislikes/triggers (Level 0 forbidden).
- Standalone: `python "{ENGINE_ROOT}/tool/add_preference.py" <like|dislike|trigger|keyword> "<content>"`
- Batch: `{"op": "add_preference", "pref_type": "<type>", "content": "<content>"}`
- Auto-appends to `character_config.json` and generates event keyword rules.

### 3. add_memory(text, mem_type, importance) — Two-Tier Memory

- **When**: Immediately call when something worth remembering happens.
- Standalone: `python "{ENGINE_ROOT}/tool/add_memory.py" [--core] [--importance N] "<text>"`
- Batch: `{"op": "add_memory", "text": "<text>", "mem_type": "recent", "importance": 1}`
- Memory content: concise summary, ≤20 chars.

**Two-tier storage:**
- `recent` (default): Short-term sliding memory, capped at `max_recent_memory` (default 50). When full, evicts by **importance** (lowest first), tie-breaking by time (oldest first).
- `core`: Permanent core memory, capped at `max_core_memory` (default 20). For key events (confessions, major conflicts, identity reveals). When full, also evicts by importance.
- `importance`: Integer 1-5, default recent=1, core=3. Items scored 4-5 are virtually immune to automatic eviction.

**Usage tips:**
- Daily interactions → `recent` + importance 1-2, let natural churn handle it
- Worth keeping long-term → `recent` + importance 3-4
- Critical turning points → `core` + importance 4-5 (≤3 per day)
- `get_context` returns all `core_memories` + last 10 `recent_memories`

### 4. record_action(action)

- **When**: After every reply, record the action descriptions used.
- Standalone: `python "{ENGINE_ROOT}/tool/record_action.py" "<action>"`
- Batch: `{"op": "record_action", "action": "<action>"}`

### 5. add_custom_item(item)

- **When**: User explicitly says "remember this action" / "save this line".
- Standalone: `python "{ENGINE_ROOT}/tool/add_custom_item.py" "<item>"`
- Batch: `{"op": "add_custom_item", "item": "<item>"}`
- **Do NOT save without user's explicit instruction or consent.**

---

## Stage Behavior Guide

> Stage is auto-calculated from 3D emotion weighted mapping, provided by `get_context`.

| Stage | Name | Guidance |
|:---:|------|------|
| 0 | Stranger | Maximum distance, rarely offers help, default cold tone |
| 1 | Colleague | Helps but tsundere; actions like "sighs softly" / "still followed" |
| 2 | Companion | Often side by side, occasionally waits, expresses worry through actions, voice occasionally softens |
| 3 | Cherished | Rarely initiates care, faint but genuine smile, silently remembers habits |

**Cross-Dimension Guidance** (real-time from `get_context`, takes priority over base stage guidance):
- High trust + low closeness → Helps but deliberately keeps distance
- High closeness + low warmth → Awkward state, care expressed through coldness
- All dimensions low → Near-stranger extreme detachment

---

## Emotion Dimension Reference

| Dimension | Range | Meaning |
|-----------|:-----:|---------|
| **trust** | 0–100 | Trust in user's competence/reliability |
| **closeness** | 0–100 | Emotional distance, willingness to accompany |
| **warmth** | -100–100 | Tone warmth: positive=soft / negative=sharp |

Each dimension decays independently (half-lives in `character_config.json`), with EMA smoothing applied on events. Scripts handle this automatically.

---

## License

MIT
