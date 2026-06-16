#!/usr/bin/env python3
"""记录一个刚使用过的动作，避免短期内重复"""
import json
import os
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(TOOL_DIR)
SETTINGS_DIR = os.path.join(ENGINE_ROOT, "settings")

STATE_FILE = os.path.join(SETTINGS_DIR, "state.json")

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
        print("用法: python record_action.py <动作描述>")
        print("示例: python record_action.py \"端起咖啡抿了一口\"")
        sys.exit(1)

    action = sys.argv[1].strip()
    state = load_state()
    state["action_history"].append(action)
    max_len = state.get("max_action_history", 20)
    if len(state["action_history"]) > max_len:
        state["action_history"] = state["action_history"][-max_len:]
    save_state(state)
    print(f"动作已记录：{action}")


if __name__ == "__main__":
    main()
