#!/usr/bin/env python3
"""读取角色状态上下文并格式化输出（v2 通用引擎版）"""
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


def output_json(state, config, stage, stage_name, cross, level, level_guide):
    """JSON 输出 — ensure_ascii 确保跨编码兼容"""
    aff = state["affection"]
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
        "memories": state.get("short_memory", [])[-10:],
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
    lines.append(f"信任:{t}  亲近:{c}  温度:{w}  阶段:{stage_name}（{stage + 1}/{len(customs) if False else 4}）")
    lines.append(f"行为指引: {guide}")
    if cross:
        lines.append("维度指引:")
        for tip in cross:
            lines.append(f"  - {tip}")
    if memories:
        lines.append("近期发生的事：")
        for m in memories[-8:]:
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
        state = {"affection": {k: v["baseline"] for k, v in dims.items()},
                 "short_memory": [], "action_history": [], "custom_actions": [],
                 "max_memory": 10, "max_action_history": 30, "max_custom_actions": 10}

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
        memories = state.get("short_memory", [])
        customs = state.get("custom_actions", [])
        recent = state.get("action_history", [])[-10:]
        output_text(aff, stage, stage_name, level, level_guide, guide, cross,
                    memories, customs, recent)


if __name__ == "__main__":
    main()
