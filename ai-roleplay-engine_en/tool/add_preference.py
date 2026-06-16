#!/usr/bin/env python3
"""AI 自我完善：将对话中发现的新偏好写入角色配置"""
import json
import os
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(TOOL_DIR)
SETTINGS_DIR = os.path.join(ENGINE_ROOT, "settings")

CONFIG_FILE = os.path.join(SETTINGS_DIR, "character_config.json")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def main():
    if len(sys.argv) < 3:
        print("用法: python add_preference.py <类型> <内容>")
        print()
        print("类型:")
        print("  like      — 角色喜欢的事物 → warmth +2 关键词")
        print("  dislike   — 角色讨厌的事物 → warmth -2 关键词")
        print("  trigger   — 情感触发词（如\"提到姐姐\"）→ 添加到事件表")
        print("  keyword   — 纯关键词（不自动生成规则，手动指定）")
        print()
        print("示例:")
        print('  python add_preference.py like "甜食"')
        print('  python add_preference.py dislike "被命令"')
        print('  python add_preference.py trigger "提到宫野明美"')
        sys.exit(1)

    pref_type = sys.argv[1].strip()
    content = sys.argv[2].strip()

    cfg = load_config()

    if pref_type == "like":
        # 追加到喜好列表
        cfg.setdefault("preferences", {}).setdefault("likes", [])
        if content not in cfg["preferences"]["likes"]:
            cfg["preferences"]["likes"].append(content)
        # 生成轻量关键词规则：提到喜好物 → 轻度升温
        new_rule = {
            "keywords": [content],
            "trust": 0, "closeness": 2, "warmth": 4,
            "note": f"auto:like:{content}"
        }
        cfg["event_table"].insert(-2, new_rule)  # 插在默认规则之前
        print(f"已添加喜好: {content}")
        print(f"自动生成规则: 提到「{content}」→ closeness+2, warmth+4")

    elif pref_type == "dislike":
        cfg.setdefault("preferences", {}).setdefault("dislikes", [])
        if content not in cfg["preferences"]["dislikes"]:
            cfg["preferences"]["dislikes"].append(content)
        new_rule = {
            "keywords": [content],
            "trust": 0, "closeness": -2, "warmth": -5,
            "note": f"auto:dislike:{content}"
        }
        cfg["event_table"].insert(-2, new_rule)
        print(f"已添加厌恶: {content}")
        print(f"自动生成规则: 提到「{content}」→ closeness-2, warmth-5")

    elif pref_type == "trigger":
        # 情感触发词 — 仅加关键词，权重较保守
        new_rule = {
            "keywords": [content],
            "trust": 0, "closeness": 3, "warmth": 2,
            "note": f"auto:trigger:{content}"
        }
        cfg["event_table"].insert(-2, new_rule)
        print(f"已添加触发词: {content}")
        print(f"自动生成规则: 提到「{content}」→ closeness+3, warmth+2")

    elif pref_type == "keyword":
        cfg.setdefault("preferences", {}).setdefault("auto_generated_keywords", [])
        if content not in cfg["preferences"]["auto_generated_keywords"]:
            cfg["preferences"]["auto_generated_keywords"].append(content)
        print(f"已添加纯关键词: {content}（未自动生成规则）")

    else:
        print(f"未知类型: {pref_type}")
        print("支持: like / dislike / trigger / keyword")
        sys.exit(1)

    save_config(cfg)


if __name__ == "__main__":
    main()
