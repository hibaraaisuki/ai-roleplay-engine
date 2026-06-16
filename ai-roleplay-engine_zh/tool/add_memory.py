#!/usr/bin/env python3
"""添加一条记忆 — 支持两段式存储（core/recent）和重要性评分（1-5）

用法:
  python add_memory.py "记忆文本"                          # 默认: recent, importance=1
  python add_memory.py --core "记忆文本"                   # core, importance=3
  python add_memory.py --importance 4 "记忆文本"           # recent, importance=4
  python add_memory.py --core --importance 5 "记忆文本"    # core, importance=5
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(TOOL_DIR)
SETTINGS_DIR = os.path.join(ENGINE_ROOT, "settings")

STATE_FILE = os.path.join(SETTINGS_DIR, "state.json")

DEFAULT_STATE = {
    "version": 3,
    "affection": {},
    "core_memory": [],
    "recent_memory": [],
    "action_history": [],
    "custom_actions": [],
    "max_core_memory": 20,
    "max_recent_memory": 50,
    "max_action_history": 100,
    "max_custom_actions": 100,
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def migrate_short_memory(state):
    """将旧版 short_memory（字符串数组）迁移为 recent_memory（对象数组）"""
    old = state.pop("short_memory", None)
    if old is None:
        return
    now = datetime.now(TZ).isoformat()
    migrated = []
    for m in old:
        if isinstance(m, dict):
            m.setdefault("importance", 1)
            m.setdefault("timestamp", now)
            migrated.append(m)
        elif isinstance(m, str):
            migrated.append({"text": m, "importance": 1, "timestamp": now})
    state["recent_memory"] = migrated


def ensure_state(state):
    """修补缺失字段，自动迁移旧格式"""
    if "short_memory" in state and "recent_memory" not in state:
        migrate_short_memory(state)
    if "version" not in state:
        state["version"] = 3 if "recent_memory" in state else 2
    for k in ("core_memory", "recent_memory"):
        state.setdefault(k, [])
    state.setdefault("max_core_memory", 20)
    state.setdefault("max_recent_memory", 50)
    state.setdefault("max_action_history", 100)
    state.setdefault("max_custom_actions", 100)


def evict_lowest(memory_list, max_len):
    """移除最低重要度的条目，同分优先移除最早的"""
    while len(memory_list) > max_len:
        min_imp = min(m.get("importance", 1) for m in memory_list)
        for i, m in enumerate(memory_list):
            if m.get("importance", 1) == min_imp:
                del memory_list[i]
                break


def main():
    mem_type = "recent"
    importance = 1
    text = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--core":
            mem_type = "core"
            if importance == 1:  # 未显式指定 importance 时 core 默认 3
                importance = 3
            i += 1
        elif args[i] == "--importance" and i + 1 < len(args):
            try:
                importance = int(args[i + 1])
                importance = max(1, min(5, importance))
            except ValueError:
                print(f"错误: importance 必须是整数 1-5，收到: {args[i + 1]}")
                sys.exit(1)
            i += 2
        elif args[i] in ("-h", "--help"):
            print("用法: python add_memory.py [--core] [--importance N] <记忆文本>")
            print()
            print("  --core              标记为核心记忆（永久保留，上限 20）")
            print("  --importance N      重要性 1-5（默认 recent=1, core=3）")
            print()
            print("示例:")
            print('  python add_memory.py "第一次一起去图书馆"')
            print('  python add_memory.py --core "用户告白了"')
            print('  python add_memory.py --core --importance 5 "用户救了我的命"')
            sys.exit(0)
        elif text is None:
            text = args[i]
            i += 1
        else:
            i += 1

    if text is None:
        print("用法: python add_memory.py [--core] [--importance N] <记忆文本>")
        print('示例: python add_memory.py "第一次一起去图书馆"')
        sys.exit(1)

    text = text.strip()
    now = datetime.now(TZ).isoformat()
    entry = {"text": text, "importance": importance, "timestamp": now}

    state = load_state()
    ensure_state(state)

    if mem_type == "core":
        state["core_memory"].append(entry)
        max_len = state.get("max_core_memory", 20)
        if len(state["core_memory"]) > max_len:
            evict_lowest(state["core_memory"], max_len)
        save_state(state)
        print(f"已记录核心记忆（重要性 {importance}）：「{text}」")
    else:
        state["recent_memory"].append(entry)
        max_len = state.get("max_recent_memory", 50)
        if len(state["recent_memory"]) > max_len:
            evict_lowest(state["recent_memory"], max_len)
        save_state(state)
        print(f"已记录记忆（重要性 {importance}）：「{text}」")


if __name__ == "__main__":
    main()
