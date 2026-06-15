#!/usr/bin/env python3
"""保存一个用户认可的专属动作或台词"""
import json
import os
import sys

STATE_FILE = r"C:\Users\Administrator\Documents\AI助手记忆\state.json"

DEFAULT_STATE = {
    "affection_stage": 0,
    "stages": ["陌生", "同僚", "同伴", "珍视"],
    "short_memory": [],
    "action_history": [],
    "custom_actions": [],
    "max_memory": 5,
    "max_action_history": 20,
    "max_custom_actions": 5
}

def load_state():
    if not os.path.exists(STATE_FILE):
        return DEFAULT_STATE.copy()
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def main():
    if len(sys.argv) < 2:
        print("用法: python add_custom_item.py <专属条目>")
        print("示例: python add_custom_item.py \"面无表情地说「无聊」但嘴角微动\"")
        sys.exit(1)

    item = sys.argv[1].strip()
    state = load_state()
    state["custom_actions"].append(item)
    max_len = state.get("max_custom_actions", 5)
    if len(state["custom_actions"]) > max_len:
        state["custom_actions"] = state["custom_actions"][-max_len:]
    save_state(state)
    print(f"已保存专属条目：「{item}」")

if __name__ == "__main__":
    main()
