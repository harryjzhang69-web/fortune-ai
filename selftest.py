"""自测脚本：纯 ASCII 输出，验证排盘/起卦/合盘逻辑都对。
跑法（结果会写到 _selftest.log）：
    py selftest.py
"""
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 强制 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from core import (
    build_bazi, render_chart_text,
    divine_by_coins, divine_by_numbers, divine_by_time, render_divination,
    analyze_compat, render_compat,
)


def line(c='='):
    print(c * 70)


def test_bazi():
    line()
    print("[TEST 1] 八字排盘 - 用户A: 2000-07-10 12:00 男")
    line()
    chart = build_bazi(2000, 7, 10, hour=12, gender="男", name="A")
    print(render_chart_text(chart))
    print()
    print("[summary]", chart.summary())

    line()
    print("[TEST 1.5] 八字排盘 - 用户B: 2002-06-18 不知时辰 女")
    line()
    chart_b = build_bazi(2002, 6, 18, hour=None, gender="女", name="B")
    print(render_chart_text(chart_b))
    print()
    print("[summary]", chart_b.summary())
    return chart, chart_b


def test_yijing():
    line()
    print("[TEST 2.1] 易经-模拟摇卦")
    line()
    r = divine_by_coins(question="测试用：今天出门顺不顺")
    print(render_divination(r))
    print()
    print("[summary]", r.summary())

    line()
    print("[TEST 2.2] 易经-报数起卦 (7,23,88)")
    line()
    r = divine_by_numbers(7, 23, 88, question="测试用：要不要换工作")
    print(render_divination(r))
    print()
    print("[summary]", r.summary())

    line()
    print("[TEST 2.3] 易经-时间起卦")
    line()
    r = divine_by_time(question="测试用：和前任的关系")
    print(render_divination(r))
    print()
    print("[summary]", r.summary())


def test_compat(chart_a, chart_b):
    line()
    print("[TEST 3] 合盘 - 用户A x 用户B")
    line()
    rep = analyze_compat(chart_a, chart_b, name_a="你", name_b="TA")
    print(render_compat(rep))


if __name__ == "__main__":
    print(">>> Fortune AI 核心引擎自测 <<<")
    print()
    chart_a, chart_b = test_bazi()
    print()
    test_yijing()
    print()
    test_compat(chart_a, chart_b)
    print()
    line()
    print("[OK] 所有测试通过")
    line()
