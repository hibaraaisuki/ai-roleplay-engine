#!/usr/bin/env python3
"""读取角色状态上下文并格式化输出（v3 两段式记忆版）"""
import json
import os
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(TOOL_DIR)
SETTINGS_DIR = os.path.join(ENGINE_ROOT, "settings")

STATE_FILE = os.path.join(SETTINGS_DIR, "state.json")
CONFIG_FILE = os.path.join(SETTINGS_DIR, "character_config.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calc_stage(affection, mapping, thresholds):
    """三维加权 → 阶段索引"""
    w = mapping["weights"]
    w_norm = (affection["warmth"] + 100) / 2.0
    score = affection["trust"] * w["trust"] + affection["closeness"] * w["closeness"] + w_norm * w["warmth"]
    for i, t in enumerate(thresholds):
        if score <= t:
            return i
    return len(thresholds)


def gen_cross_guidance(affection, config):
    """生成维度交叉指引"""
    ct = config.get("cross_thresholds", {})
    cg = config.get("cross_guidance", {})
    tips = []

    t = affection["trust"]
    c = affection["closeness"]
    w = affection["warmth"]

    if cg.get("high_trust") and t >= ct.get("trust_high", 70):
        tips.append(cg["high_trust"])
    elif cg.get("low_trust") and t <= ct.get("trust_low", 30):
        tips.append(cg["low_trust"])

    if cg.get("high_closeness") and c >= ct.get("closeness_high", 70):
        tips.append(cg["high_closeness"])
    elif cg.get("low_closeness") and c <= ct.get("closeness_low", 30):
        tips.append(cg["low_closeness"])

    if cg.get("high_warmth") and w >= ct.get("warmth_high", 50):
        tips.append(cg["high_warmth"])
    elif cg.get("low_warmth") and w <= ct.get("warmth_low", -30):
        tips.append(cg["low_warmth"])

    tcl = ct.get("trust_high_close_low", [65, 35])
    if cg.get("trust_high_close_low") and t >= tcl[0] and c <= tcl[1]:
        tips.append(cg["trust_high_close_low"])

    chl = ct.get("close_high_warm_low", [65, -10])
    if cg.get("close_high_warm_low") and c >= chl[0] and w <= chl[1]:
        tips.append(cg["close_high_warm_low"])

    al = ct.get("all_low", [35, 35, -20])
    if cg.get("all_low") and t <= al[0] and c <= al[1] and w <= al[2]:
        tips.append(cg["all_low"])

    return tips


def get_memories_json(state):
    """提取两段式记忆（兼容旧版 short_memory）"""
    # 核心记忆 — 返回全部
    core = state.get("core_memory", [])
    core_out = [{"text": m["text"], "importance": m.get("importance", 1)} for m in core]

    # 近期记忆 — 最近 10 条
    if "recent_memory" in state:
        recent = state["recent_memory"][-10:]
        recent_out = [{"text": m["text"], "importance": m.get("importance", 1)} for m in recent]
    elif "short_memory" in state:
        # 旧格式兼容
        old = state["short_memory"][-10:]
        recent_out = [{"text": m, "importance": 1} if isinstance(m, str) else
                       {"text": m["text"], "importance": m.get("importance", 1)} for m in old]
    else:
        recent_out = []

    return core_out, recent_out


def get_memories_text(state):
    """提取记忆文本列表（兼容旧版）"""
    core = state.get("core_memory", [])
    if "recent_memory" in state:
        recent = state["recent_memory"][-8:]
        all_memories = [m["text"] for m in core] + [m["text"] for m in recent]
    elif "short_memory" in state:
        all_memories = state["short_memory"][-8:]
    else:
        all_memories = []
    return all_memories


def output_json(state, config, stage, stage_name, cross, level, level_guide):
    """JSON 输出 — ensure_ascii 确保跨编码兼容"""
    aff = state["affection"]
    core_mem, recent_mem = get_memories_json(state)

    result = {
        "processing_level": level,
        "processing_level_guide": level_guide,
        "affection": {
            "trust": round(aff["trust"]),
            "closeness": round(aff["closeness"]),
            "warmth": round(aff["warmth"])
        },
        "stage": {
            "index": stage,
            "name": stage_name,
            "total": len(config["stages"])
        },
        "guidance": {
            "stage": config.get("stage_guides", {}).get(str(stage), ""),
            "cross": cross
        },
        "core_memories": core_mem,
        "recent_memories": recent_mem,
        "action_history": state.get("action_history", [])[-10:],
        "custom_actions": state.get("custom_actions", [])
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))


def output_text(affection, stage, stage_name, level, level_guide, guide, cross,
                memories, customs, recent):
    """原始文本输出（保留向后兼容）"""
    lines = []
    lines.append(f"处理档位: Level {level} — {level_guide}")
    t, c, w = round(affection["trust"]), round(affection["closeness"]), round(affection["warmth"])
    lines.append(f"信任:{t}  亲近:{c}  温度:{w}  阶段:{stage_name}（{stage + 1}/4）")
    lines.append(f"行为指引: {guide}")
    if cross:
        lines.append("维度指引:")
        for tip in cross:
            lines.append(f"  - {tip}")
    if memories:
        lines.append("近期发生的事：")
        for m in memories[-8:]:
            if isinstance(m, dict):
                imp = m.get("importance", 1)
                star = "★" * imp + "☆" * (5 - imp)
                lines.append(f"  - [{star}] {m['text']}")
            else:
                lines.append(f"  - {m}")
    if customs:
        lines.append("用户保存的专属动作/台词（可轮换）：")
        for ci in customs:
            lines.append(f"  - {ci}")
    if recent:
        lines.append("最近用过的动作（请避免重复）：")
        for a in recent:
            lines.append(f"  - {a}")
    print("\n".join(lines))


def main():
    use_json = "--json" in sys.argv

    config = load_json(CONFIG_FILE)
    stage_mapping = config["stage_mapping"]
    thresholds = stage_mapping["thresholds"]
    stages = config["stages"]

    if os.path.exists(STATE_FILE):
        state = load_json(STATE_FILE)
    else:
        dims = config["dimensions"]
        state = {
            "version": 3,
            "affection": {k: v["baseline"] for k, v in dims.items()},
            "core_memory": [],
            "recent_memory": [],
            "action_history": [],
            "custom_actions": [],
            "max_core_memory": 20,
            "max_recent_memory": 50,
            "max_action_history": 100,
            "max_custom_actions": 100,
        }

    aff = state["affection"]
    stage = calc_stage(aff, stage_mapping, thresholds)
    stage_name = stages[stage] if stage < len(stages) else stages[-1]
    guide = config.get("stage_guides", {}).get(str(stage), "")
    cross = gen_cross_guidance(aff, config)
    level = config.get("processing_level", 1)
    level_guide = config.get("_processing_level_guide", {}).get(str(level), "")

    if use_json:
        output_json(state, config, stage, stage_name, cross, level, level_guide)
    else:
        memories = get_memories_text(state)
        customs = state.get("custom_actions", [])
        recent = state.get("action_history", [])[-10:]
        output_text(aff, stage, stage_name, level, level_guide, guide, cross,
                    memories, customs, recent)


if __name__ == "__main__":
    main()
