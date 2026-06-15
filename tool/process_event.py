#!/usr/bin/env python3
"""通用情感事件引擎 — 读取角色配置，执行分类/衰减/EMA/输出"""
import json
import os
import sys
import math
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))  # UTC+8

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(TOOL_DIR)
SETTINGS_DIR = os.path.join(ENGINE_ROOT, "settings")

STATE_FILE = os.path.join(SETTINGS_DIR, "state.json")
CONFIG_FILE = os.path.join(SETTINGS_DIR, "character_config.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def classify_event(text, event_table):
    """关键词匹配，返回三维 event delta。按 table 顺序优先匹配"""
    for entry in event_table:
        for kw in entry["keywords"]:
            if kw in text:
                return (entry["trust"], entry["closeness"], entry["warmth"])
    return (0, 1, 1)  # 默认：日常互动


def apply_decay(affection, dims):
    """指数衰减：V = baseline + (V - baseline) * e^(-k * days)"""
    last = affection.get("last_update")
    if last is None:
        return
    try:
        last_dt = datetime.fromisoformat(last)
    except (ValueError, TypeError):
        return
    now = datetime.now(TZ)
    days = (now - last_dt).total_seconds() / 86400.0
    if days <= 0.01:
        return
    for dim_key, cfg in dims.items():
        k = math.log(2) / cfg["half_life_days"]
        old = affection[dim_key]
        affection[dim_key] = cfg["baseline"] + (old - cfg["baseline"]) * math.exp(-k * days)


def apply_ema(affection, event_deltas, alpha):
    """EMA 平滑：new = old + event_delta × α"""
    dims = ["trust", "closeness", "warmth"]
    for i, key in enumerate(dims):
        if event_deltas[i] != 0:
            affection[key] += event_deltas[i] * alpha


def clamp_affection(affection, dims):
    """限幅"""
    for key, cfg in dims.items():
        affection[key] = max(cfg["min"], min(cfg["max"], affection[key]))


def calc_stage(affection, mapping, thresholds):
    """三维加权 → 阶段索引"""
    w = mapping["weights"]
    w_norm = (affection["warmth"] + 100) / 2.0  # -100~100 → 0~100
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

    # 交叉组合
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


def format_output(affection, old_affection, stage, stage_name, stage_guides, cross_tips):
    """格式化输出"""
    dims = ["trust", "closeness", "warmth"]
    labels = ["信任", "亲近", "温度"]

    parts = []
    for key, label in zip(dims, labels):
        new = round(affection[key])
        old = round(old_affection[key])
        d = new - old
        parts.append(f"{label}:{new}({d:+d})")

    lines = [
        "  ".join(parts) + f"  阶段:{stage_name}",
        f"行为指引: {stage_guides.get(str(stage), '')}",
    ]
    if cross_tips:
        lines.append("维度提示: " + "；".join(cross_tips))
    else:
        lines.append("维度提示: 维度均衡，按阶段默认指引即可")

    print("\n".join(lines))


def main():
    if len(sys.argv) < 2:
        print("用法: python process_event.py \"<事件描述文本>\"")
        sys.exit(1)

    text = sys.argv[1].strip()

    # 加载配置
    config = load_json(CONFIG_FILE)
    event_table = config["event_table"]
    dims = config["dimensions"]
    alpha = config.get("ema_alpha", 0.3)
    stage_mapping = config["stage_mapping"]
    thresholds = stage_mapping["thresholds"]
    stages = config["stages"]
    stage_guides = config.get("stage_guides", {})

    # 加载状态
    if os.path.exists(STATE_FILE):
        state = load_json(STATE_FILE)
    else:
        state = {"affection": {k: v["baseline"] for k, v in dims.items()},
                 "short_memory": [], "action_history": [], "custom_actions": [],
                 "max_memory": 10, "max_action_history": 30, "max_custom_actions": 10, "version": 2}
    if "affection" not in state:
        state["affection"] = {k: v["baseline"] for k, v in dims.items()}
        state["version"] = 2
    for k in dims:
        state["affection"].setdefault(k, dims[k]["baseline"])
    state["affection"].setdefault("last_update", None)
    for k in ("max_memory", "max_action_history", "max_custom_actions"):
        state.setdefault(k, 10)

    old_affection = {k: state["affection"][k] for k in dims}

    # 1. 事件分类
    event_deltas = classify_event(text, event_table)

    # 2. 指数衰减
    apply_decay(state["affection"], dims)

    # 3. EMA 平滑
    apply_ema(state["affection"], event_deltas, alpha)

    # 4. 限幅
    clamp_affection(state["affection"], dims)

    # 5. 更新时间戳
    state["affection"]["last_update"] = datetime.now(TZ).isoformat()

    # 6. 保存
    save_json(STATE_FILE, state)

    # 7. 计算阶段 + 交叉指引 + 输出
    stage = calc_stage(state["affection"], stage_mapping, thresholds)
    stage_name = stages[stage] if stage < len(stages) else stages[-1]
    cross_tips = gen_cross_guidance(state["affection"], config)

    format_output(state["affection"], old_affection, stage, stage_name, stage_guides, cross_tips)


if __name__ == "__main__":
    main()
