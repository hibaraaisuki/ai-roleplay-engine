#!/usr/bin/env python3
"""批量情感引擎操作 — 单次读写 state.json，所有操作在内存中顺序执行后统一写回。

用法（推荐 --input 文件传参，避免 shell 编码损坏）:
  python batch.py --input <json文件路径>

备选（仅纯 ASCII 安全）:
  echo '[...]' | python batch.py

输出: ensure_ascii 纯 ASCII JSON 数组，每项对应一个操作的结果。
"""
import json
import os
import sys
import math
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=8))

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_ROOT = os.path.dirname(TOOL_DIR)
SETTINGS_DIR = os.path.join(ENGINE_ROOT, "settings")

STATE_FILE = os.path.join(SETTINGS_DIR, "state.json")
CONFIG_FILE = os.path.join(SETTINGS_DIR, "character_config.json")


# ============================================================
#  JSON I/O
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
#  共享引擎逻辑（内联自 process_event.py / get_context.py）
# ============================================================

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
    score = (
        affection["trust"] * w["trust"]
        + affection["closeness"] * w["closeness"]
        + w_norm * w["warmth"]
    )
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


# ============================================================
#  默认状态构造（v2 格式，从 config baselines 初始化）
# ============================================================

def make_default_state(config):
    """从 character_config.json 的维度基线创建 v2 格式默认状态"""
    dims = config["dimensions"]
    return {
        "version": 2,
        "affection": {k: v["baseline"] for k, v in dims.items()},
        "short_memory": [],
        "action_history": [],
        "custom_actions": [],
        "max_memory": 100,
        "max_action_history": 100,
        "max_custom_actions": 100,
    }


def ensure_state(state, dims):
    """修补 state 中缺失的 key，保证后续处理不报错"""
    if "affection" not in state:
        state["affection"] = {k: v["baseline"] for k, v in dims.items()}
        state["version"] = 2
    for k in dims:
        state["affection"].setdefault(k, dims[k]["baseline"])
    state["affection"].setdefault("last_update", None)
    for k in ("max_memory", "max_action_history", "max_custom_actions"):
        state.setdefault(k, 100)
    for k in ("short_memory", "action_history", "custom_actions"):
        state.setdefault(k, [])


# ============================================================
#  操作 Handler（每个返回 data dict，出错抛异常）
# ============================================================

def handle_get_context(state, config):
    """返回当前上下文快照（读操作，不改动 state）"""
    stage_mapping = config["stage_mapping"]
    thresholds = stage_mapping["thresholds"]
    stages = config["stages"]
    stage_guides = config.get("stage_guides", {})

    aff = state["affection"]
    stage_idx = calc_stage(aff, stage_mapping, thresholds)
    stage_name = stages[stage_idx] if stage_idx < len(stages) else stages[-1]
    cross = gen_cross_guidance(aff, config)
    if not cross:
        cross = ["维度均衡，按阶段默认指引即可"]

    level = config.get("processing_level", 1)
    level_guide = config.get("_processing_level_guide", {}).get(str(level), "")

    return {
        "processing_level": level,
        "processing_level_guide": level_guide,
        "affection": {
            "trust": round(aff["trust"]),
            "closeness": round(aff["closeness"]),
            "warmth": round(aff["warmth"]),
        },
        "stage": {
            "index": stage_idx,
            "name": stage_name,
            "total": len(stages),
        },
        "guidance": {
            "stage": stage_guides.get(str(stage_idx), ""),
            "cross": cross,
        },
        "memories": state.get("short_memory", [])[-10:],
        "action_history": state.get("action_history", [])[-10:],
        "custom_actions": state.get("custom_actions", []),
    }


def handle_process_event(state, config, event_text):
    """处理情感事件 — 衰减 → 分类 → EMA → 限幅 → 更新 time"""
    if not event_text or not event_text.strip():
        raise ValueError("事件文本为空")

    event_text = event_text.strip()
    event_table = config["event_table"]
    dims = config["dimensions"]
    alpha = config.get("ema_alpha", 0.3)
    stage_mapping = config["stage_mapping"]
    thresholds = stage_mapping["thresholds"]
    stages = config["stages"]
    stage_guides = config.get("stage_guides", {})

    old_affection = {k: state["affection"][k] for k in dims}

    event_deltas = classify_event(event_text, event_table)
    apply_decay(state["affection"], dims)
    apply_ema(state["affection"], event_deltas, alpha)
    clamp_affection(state["affection"], dims)
    state["affection"]["last_update"] = datetime.now(TZ).isoformat()

    stage_idx = calc_stage(state["affection"], stage_mapping, thresholds)
    stage_name = stages[stage_idx] if stage_idx < len(stages) else stages[-1]
    cross = gen_cross_guidance(state["affection"], config)
    if not cross:
        cross = ["维度均衡，按阶段默认指引即可"]

    dims_keys = ["trust", "closeness", "warmth"]
    dims_cn = ["信任", "亲近", "温度"]
    affection_out = {}
    for key, label in zip(dims_keys, dims_cn):
        new_val = round(state["affection"][key])
        old_val = round(old_affection[key])
        affection_out[key] = {
            "label": label,
            "new": new_val,
            "old": old_val,
            "delta": new_val - old_val,
        }

    return {
        "affection": affection_out,
        "stage": {"index": stage_idx, "name": stage_name, "total": len(stages)},
        "guidance": {
            "stage": stage_guides.get(str(stage_idx), ""),
            "cross": cross,
        },
    }


def handle_add_memory(state, text):
    """追加短期记忆"""
    if not text or not text.strip():
        raise ValueError("记忆文本为空")
    text = text.strip()
    state["short_memory"].append(text)
    max_len = state.get("max_memory", 100)
    if len(state["short_memory"]) > max_len:
        state["short_memory"] = state["short_memory"][-max_len:]
    return {"recorded": text, "memory_count": len(state["short_memory"])}


def handle_record_action(state, action):
    """记录动作"""
    if not action or not action.strip():
        raise ValueError("动作文本为空")
    action = action.strip()
    state["action_history"].append(action)
    max_len = state.get("max_action_history", 100)
    if len(state["action_history"]) > max_len:
        state["action_history"] = state["action_history"][-max_len:]
    return {"recorded": action, "action_count": len(state["action_history"])}


def handle_add_custom_item(state, item):
    """保存专属动作/台词"""
    if not item or not item.strip():
        raise ValueError("条目文本为空")
    item = item.strip()
    state["custom_actions"].append(item)
    max_len = state.get("max_custom_actions", 100)
    if len(state["custom_actions"]) > max_len:
        state["custom_actions"] = state["custom_actions"][-max_len:]
    return {"saved": item, "custom_count": len(state["custom_actions"])}


def handle_add_preference(config, pref_type, content):
    """追加偏好到 character_config.json — 返回 (data_dict, mutated)"""
    valid_types = ("like", "dislike", "trigger", "keyword")
    if pref_type not in valid_types:
        raise ValueError(f"未知偏好类型: {pref_type}，支持: {', '.join(valid_types)}")
    if not content or not content.strip():
        raise ValueError("偏好内容为空")
    content = content.strip()

    config.setdefault("preferences", {})
    config.setdefault("event_table", [])

    if pref_type == "like":
        config["preferences"].setdefault("likes", [])
        if content not in config["preferences"]["likes"]:
            config["preferences"]["likes"].append(content)
        new_rule = {
            "keywords": [content],
            "trust": 0,
            "closeness": 2,
            "warmth": 4,
            "note": f"auto:like:{content}",
        }
        config["event_table"].insert(-2, new_rule)
        msg = f"已添加喜好: {content}，自动生成规则: closeness+2, warmth+4"

    elif pref_type == "dislike":
        config["preferences"].setdefault("dislikes", [])
        if content not in config["preferences"]["dislikes"]:
            config["preferences"]["dislikes"].append(content)
        new_rule = {
            "keywords": [content],
            "trust": 0,
            "closeness": -2,
            "warmth": -5,
            "note": f"auto:dislike:{content}",
        }
        config["event_table"].insert(-2, new_rule)
        msg = f"已添加厌恶: {content}，自动生成规则: closeness-2, warmth-5"

    elif pref_type == "trigger":
        new_rule = {
            "keywords": [content],
            "trust": 0,
            "closeness": 3,
            "warmth": 2,
            "note": f"auto:trigger:{content}",
        }
        config["event_table"].insert(-2, new_rule)
        msg = f"已添加触发词: {content}，自动生成规则: closeness+3, warmth+2"

    elif pref_type == "keyword":
        config["preferences"].setdefault("auto_generated_keywords", [])
        if content not in config["preferences"]["auto_generated_keywords"]:
            config["preferences"]["auto_generated_keywords"].append(content)
        msg = f"已添加纯关键词: {content}（未自动生成规则）"

    return (
        {"type": pref_type, "content": content, "message": msg},
        True,
    )


# ============================================================
#  Main
# ============================================================

HANDLERS = {
    "get_context": handle_get_context,
    "process_event": handle_process_event,
    "add_memory": handle_add_memory,
    "record_action": handle_record_action,
    "add_custom_item": handle_add_custom_item,
    "add_preference": handle_add_preference,
}

# 每个 op 对应 handler 需要的额外参数：0=仅 state, 1=state+config, 2=config（写）
HANDLER_STYLE = {
    "get_context": "state_config",
    "process_event": "state_config",
    "add_memory": "state_only",
    "record_action": "state_only",
    "add_custom_item": "state_only",
    "add_preference": "config_only",
}


def main():
    # 解析输入来源
    input_path = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_path = args[i + 1]
            i += 2
        elif args[i] in ("-h", "--help"):
            print("用法: batch.py [--input <json文件>]")
            print()
            print("从 stdin 读取 JSON 操作数组并批量执行。")
            print("也支持 --input 指定 JSON 文件路径（避免 shell 转义问题）。")
            print()
            print("输入格式: JSON 数组，每项含 \"op\" 字段及操作特定字段。")
            print("支持的操作: get_context, process_event, add_memory,")
            print("            record_action, add_custom_item, add_preference")
            sys.exit(0)
        else:
            i += 1

    # 读取输入 JSON
    if input_path:
        with open(input_path, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()

    if not raw or not raw.strip():
        print(json.dumps([{"op": None, "status": "error", "error": "输入为空，请提供 JSON 操作数组", "data": None}],
                         ensure_ascii=True, indent=2))
        sys.exit(1)

    try:
        ops = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps([{"op": None, "status": "error", "error": f"输入 JSON 解析失败: {e}", "data": None}],
                         ensure_ascii=True, indent=2))
        sys.exit(1)

    if not isinstance(ops, list):
        print(json.dumps([{"op": None, "status": "error", "error": "输入必须是 JSON 数组", "data": None}],
                         ensure_ascii=True, indent=2))
        sys.exit(1)

    if not ops:
        print(json.dumps([{"op": None, "status": "error", "error": "操作数组为空", "data": None}],
                         ensure_ascii=True, indent=2))
        sys.exit(1)

    # 限制单批次最大操作数
    if len(ops) > 50:
        print(json.dumps([{"op": None, "status": "error",
                           "error": f"操作数 ({len(ops)}) 超过上限 (50)", "data": None}],
                         ensure_ascii=True, indent=2))
        sys.exit(1)

    # 加载配置（必须成功，否则无法继续）
    try:
        config = load_json(CONFIG_FILE)
    except Exception as e:
        print(json.dumps([{"op": None, "status": "error",
                           "error": f"无法加载 character_config.json: {e}", "data": None}],
                         ensure_ascii=True, indent=2))
        sys.exit(1)

    dims = config.get("dimensions", {})

    # 加载状态
    if os.path.exists(STATE_FILE):
        try:
            state = load_json(STATE_FILE)
        except Exception as e:
            print(json.dumps([{"op": None, "status": "error",
                               "error": f"state.json 存在但解析失败: {e}", "data": None}],
                             ensure_ascii=True, indent=2))
            sys.exit(1)
    else:
        state = make_default_state(config)

    ensure_state(state, dims)

    # 跟踪 config 是否被修改
    config_mutated = False

    # 顺序执行操作
    results = []
    for idx, op in enumerate(ops):
        if not isinstance(op, dict):
            results.append({
                "op": None,
                "status": "error",
                "error": f"操作 #{idx} 不是 JSON 对象",
                "data": None,
            })
            continue

        op_type = op.get("op", "")
        if op_type not in HANDLERS:
            results.append({
                "op": op_type or None,
                "status": "error",
                "error": f"未知操作类型: {op_type}，支持: {', '.join(HANDLERS.keys())}",
                "data": None,
            })
            continue

        try:
            handler = HANDLERS[op_type]
            style = HANDLER_STYLE[op_type]

            if style == "state_only":
                # add_memory / record_action / add_custom_item
                arg_map = {
                    "add_memory": ("text",),
                    "record_action": ("action",),
                    "add_custom_item": ("item",),
                }
                field = arg_map[op_type][0]
                if field not in op or not op[field]:
                    raise ValueError(f"缺少必填字段: {field}")
                data = handler(state, op[field])

            elif style == "state_config":
                # get_context / process_event
                if op_type == "get_context":
                    data = handler(state, config)
                elif op_type == "process_event":
                    if "event" not in op or not op.get("event"):
                        raise ValueError("缺少必填字段: event")
                    data = handler(state, config, op["event"])

            elif style == "config_only":
                # add_preference
                pref_type = op.get("pref_type", "")
                content = op.get("content", "")
                data, mutated = handler(config, pref_type, content)
                if mutated:
                    config_mutated = True

            results.append({"op": op_type, "status": "ok", "data": data})

        except Exception as e:
            results.append({
                "op": op_type,
                "status": "error",
                "error": str(e),
                "data": None,
            })

    # 写回 state.json（仅一次）
    try:
        save_json(STATE_FILE, state)
    except Exception as e:
        results.append({
            "op": "_save_state",
            "status": "error",
            "error": f"写回 state.json 失败: {e}",
            "data": None,
        })

    # 写回 character_config.json（仅当被修改时）
    if config_mutated:
        try:
            save_json(CONFIG_FILE, config)
        except Exception as e:
            results.append({
                "op": "_save_config",
                "status": "error",
                "error": f"写回 character_config.json 失败: {e}",
                "data": None,
            })

    # 输出
    print(json.dumps(results, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
