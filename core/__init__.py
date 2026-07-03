"""core 包入口：纯计算的命理引擎，不依赖大模型。"""
from .bazi import build_bazi, render_chart_text, BaziChart
from .yijing import (
    divine_by_coins, divine_by_numbers, divine_by_time,
    render_divination, DivinationResult,
)
from .compat import analyze_compat, render_compat, CompatReport

__all__ = [
    "build_bazi", "render_chart_text", "BaziChart",
    "divine_by_coins", "divine_by_numbers", "divine_by_time",
    "render_divination", "DivinationResult",
    "analyze_compat", "render_compat", "CompatReport",
]
