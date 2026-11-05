#!/usr/bin/env python3
"""平台去杠杆信号打分。

输入 CSV：每行一期，列为 date、各指标（0=绿 1=黄 2=红，留空=本期无数据）、note。
指标定义与阈值见同目录 README.md。只依赖标准库。
"""

import argparse
import csv
import sys

CATEGORIES = {
    "PB 数据": (0.40, ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]),
    "VIX 期限结构": (0.30, ["V1", "V2", "V3", "V4", "V5", "V6"]),
    "SPX 期权价差": (0.30, ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]),
}

# 三者同时为红，直接判定为平台式去杠杆
HARD_RULE = ("V1", "P4", "S5")

LEVELS = [
    (0.70, "🔴 平台式去杠杆"),
    (0.50, "🟠 去杠杆进行中"),
    (0.25, "🟡 升温"),
    (0.00, "🟢 平静"),
]


def parse_value(row, key):
    raw = (row.get(key) or "").strip()
    if raw == "":
        return None
    value = int(raw)
    if value not in (0, 1, 2):
        raise ValueError(f"{row.get('date')} {key}={raw}：只能是 0/1/2 或留空")
    return value


def score_row(row):
    values = {
        key: parse_value(row, key)
        for _, keys in CATEGORIES.values()
        for key in keys
    }

    cat_scores = {}
    total = 0.0
    weight_used = 0.0
    for name, (weight, keys) in CATEGORIES.items():
        present = [values[k] for k in keys if values[k] is not None]
        if not present:
            cat_scores[name] = None
            continue
        ratio = sum(present) / (2 * len(present))
        cat_scores[name] = ratio
        total += weight * ratio
        weight_used += weight

    # 某一类整期缺失时，按剩余类别的权重重新归一化
    composite = total / weight_used if weight_used else 0.0
    hard_hit = all(values[k] == 2 for k in HARD_RULE)
    red_flags = [k for k, v in values.items() if v == 2]

    if hard_hit:
        status = "🔴 平台式去杠杆（硬规则触发）"
    else:
        status = next(label for floor, label in LEVELS if composite >= floor)

    return cat_scores, composite, status, red_flags


def main():
    parser = argparse.ArgumentParser(description="平台去杠杆信号打分")
    parser.add_argument("csv_path", help="信号记录 CSV，例如 signals_log.csv")
    parser.add_argument("--last", action="store_true", help="只显示最新一期")
    args = parser.parse_args()

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("date") or "").strip()]

    if not rows:
        sys.exit("CSV 里没有数据行")
    if args.last:
        rows = rows[-1:]

    for row in rows:
        cat_scores, composite, status, red_flags = score_row(row)
        print(f"== {row['date']}  综合 {composite:.0%}  {status}")
        for name, ratio in cat_scores.items():
            shown = "无数据" if ratio is None else f"{ratio:.0%}"
            print(f"   {name:<10} {shown}")
        if red_flags:
            print(f"   红灯：{', '.join(red_flags)}")
        note = (row.get("note") or "").strip()
        if note:
            print(f"   备注：{note}")


if __name__ == "__main__":
    main()
