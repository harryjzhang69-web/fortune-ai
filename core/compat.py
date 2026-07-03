"""
合盘分析（双人匹配）
基于八字进行简化的合盘分析，输出：
  - 双方日主关系（生克）
  - 五行互补情况
  - 月令节奏
  - 综合相处特点
不算"婚姻吉凶"——避免迷信，做"性格匹配 + 相处倾向"的参考。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .bazi import BaziChart, GAN_WUXING, GAN_YINYANG


# 五行生克
SHENG = {  # A 生 B
    "木": "火", "火": "土", "土": "金", "金": "水", "水": "木"
}
KE = {     # A 克 B
    "木": "土", "土": "水", "水": "火", "火": "金", "金": "木"
}


def _wuxing_relation(wx_a: str, wx_b: str) -> str:
    """A 对 B 的关系"""
    if wx_a == wx_b:
        return "同"
    if SHENG.get(wx_a) == wx_b:
        return "生"
    if SHENG.get(wx_b) == wx_a:
        return "被生"
    if KE.get(wx_a) == wx_b:
        return "克"
    if KE.get(wx_b) == wx_a:
        return "被克"
    return "无"


@dataclass
class CompatReport:
    """合盘报告"""
    person_a_name: str = "A"
    person_b_name: str = "B"
    summary_a: str = ""
    summary_b: str = ""

    rizhu_relation: str = ""        # 日主关系：A 的 X 对 B 的 Y 是什么关系
    rizhu_explain: str = ""         # 日主关系的解读

    wuxing_complement: dict = field(default_factory=dict)  # 五行互补情况
    common_lacking: list[str] = field(default_factory=list)  # 共同缺失
    complement_score: int = 0        # 互补分数 0-100

    chemistry: str = ""              # 化学反应描述（"互补/相似/张力/冲突"）
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    advice: str = ""

    overall: str = ""                # 综合评语


def analyze_compat(chart_a: BaziChart, chart_b: BaziChart,
                   name_a: str = "你", name_b: str = "TA") -> CompatReport:
    rep = CompatReport(person_a_name=name_a, person_b_name=name_b)
    rep.summary_a = chart_a.summary()
    rep.summary_b = chart_b.summary()

    # ===== 日主关系 =====
    wx_a = chart_a.rizhu_wuxing
    wx_b = chart_b.rizhu_wuxing
    rel = _wuxing_relation(wx_a, wx_b)
    yy_a = chart_a.rizhu_yinyang
    yy_b = chart_b.rizhu_yinyang
    rel_desc = {
        "同": f"日主同为{wx_a}",
        "生": f"{name_a}的{wx_a}生{name_b}的{wx_b}",
        "被生": f"{name_b}的{wx_b}生{name_a}的{wx_a}",
        "克": f"{name_a}的{wx_a}克{name_b}的{wx_b}",
        "被克": f"{name_b}的{wx_b}克{name_a}的{wx_a}",
    }.get(rel, "无明显生克")
    rep.rizhu_relation = rel_desc

    # 日主关系解读（这是合盘最重要的一段）
    if rel == "同":
        if yy_a == yy_b:
            rep.rizhu_explain = (
                f"两人日主同为{yy_a}{wx_a}，性格底色高度相似——容易'秒懂'对方，"
                f"但也容易'同质化'：相似的优点会共振，相似的短板也会共鸣。"
                f"长期相处需要谁先一步成长来打破镜像。"
            )
        else:
            rep.rizhu_explain = (
                f"两人日主同为{wx_a}，但阴阳互补（{yy_a}vs{yy_b}）——"
                f"这是非常协调的组合：方向一致，但表达方式互补，磨合成本低。"
            )
    elif rel == "生":
        rep.rizhu_explain = (
            f"{name_a}（{wx_a}）生{name_b}（{wx_b}）——"
            f"在关系里，{name_a}是付出方、滋养方，{name_b}是被照顾方。"
            f"这种关系{name_a}容易心甘情愿地给，但要警惕长期单向付出导致的疲惫。"
        )
    elif rel == "被生":
        rep.rizhu_explain = (
            f"{name_b}（{wx_b}）生{name_a}（{wx_a}）——"
            f"在关系里，{name_b}是付出方、滋养方，{name_a}是被照顾方。"
            f"如果{name_a}知道感恩、懂得回应，这种关系会很温暖；"
            f"反之则容易让{name_b}耗能。"
        )
    elif rel == "克":
        rep.rizhu_explain = (
            f"{name_a}（{wx_a}）克{name_b}（{wx_b}）——"
            f"⚠️ '克'不等于'坏'：在感情里，往往表现为{name_a}是更主导、更拿主意的一方，"
            f"{name_b}会受{name_a}影响、改变。"
            f"如果{name_b}本身{wx_b}旺（受得住），是良性激发；"
            f"如果{name_b}本身{wx_b}弱，则容易变成压制和消耗。"
        )
    elif rel == "被克":
        rep.rizhu_explain = (
            f"{name_b}（{wx_b}）克{name_a}（{wx_a}）——"
            f"⚠️ 在感情里，{name_b}对{name_a}是激发型/塑造型的存在。"
            f"如果{name_a}本身{wx_a}旺，是被'煅炼'，越磨越成器；"
            f"如果{name_a}本身{wx_a}弱，则容易感到被压制、被消耗。"
            f"看双方的整体强弱来定。"
        )

    # ===== 五行互补 =====
    dist_a = chart_a.wuxing_dist.to_dict()
    dist_b = chart_b.wuxing_dist.to_dict()

    complement = {}
    pros = []
    cons = []
    score = 50

    for wx in ["金", "木", "水", "火", "土"]:
        a_val = dist_a[wx]
        b_val = dist_b[wx]
        if a_val == 0 and b_val > 0:
            complement[wx] = f"{name_a}缺{wx}，{name_b}有（{b_val}个）—— {name_b}能补{name_a}"
            pros.append(f"{name_b}的{wx}能补{name_a}的缺")
            score += 8
        elif b_val == 0 and a_val > 0:
            complement[wx] = f"{name_b}缺{wx}，{name_a}有（{a_val}个）—— {name_a}能补{name_b}"
            pros.append(f"{name_a}的{wx}能补{name_b}的缺")
            score += 8
        elif a_val == 0 and b_val == 0:
            complement[wx] = f"两人都缺{wx} ⚠️"
            cons.append(f"双方都缺{wx}（{wx}代表的能量是共同短板）")
            rep.common_lacking.append(wx)
            score -= 5

    rep.wuxing_complement = complement
    rep.complement_score = max(0, min(100, score))

    # ===== 化学反应 =====
    if rel in ("克", "被克"):
        rep.chemistry = "互补且有张力——吸引力强，但需要消耗"
    elif rel in ("生", "被生"):
        rep.chemistry = "温和滋养——温暖，但容易出现单向付出"
    elif rel == "同":
        rep.chemistry = "镜像同频——容易理解对方，但缺少新刺激"
    else:
        rep.chemistry = "中性——没有强烈的化学反应"

    # ===== 月令节奏 =====
    a_month_zhi = chart_a.month.zhi
    b_month_zhi = chart_b.month.zhi
    # 季节相似度（粗判）
    seasons = {
        "寅卯辰": "春", "巳午未": "夏",
        "申酉戌": "秋", "亥子丑": "冬",
    }
    a_season = next((s for k, s in seasons.items() if a_month_zhi in k), "?")
    b_season = next((s for k, s in seasons.items() if b_month_zhi in k), "?")
    if a_season == b_season:
        pros.append(f"两人都生于{a_season}季，情绪节奏相近")
    else:
        # 春秋、夏冬属于对冲季节
        opposites = {("春", "秋"), ("秋", "春"), ("夏", "冬"), ("冬", "夏")}
        if (a_season, b_season) in opposites:
            cons.append(f"{name_a}生于{a_season}、{name_b}生于{b_season}，节奏反向，需磨合")
        else:
            pros.append(f"季节{a_season}/{b_season}邻近，节奏可调和")

    # ===== 建议 =====
    if rep.common_lacking:
        rep.advice = (
            f"双方共同缺{'/'.join(rep.common_lacking)}——"
            f"建议关系里有意识地引入对应能量"
            f"（比如缺木 → 一起做有方向感、有规划的事；"
            f"缺火 → 多创造仪式感和热情；"
            f"缺水 → 多沟通、多表达；"
            f"缺金 → 多守原则、有界限感；"
            f"缺土 → 多创造稳定的共同体验）。"
        )
    else:
        rep.advice = "五行互补尚可，关键是把吸引转化为长期的共同方向。"

    rep.pros = pros
    rep.cons = cons

    # ===== 综合评语 =====
    if rep.complement_score >= 70:
        verdict = "互补性较好"
    elif rep.complement_score >= 50:
        verdict = "互补性中等，有相处张力"
    else:
        verdict = "互补性偏弱，磨合成本较高"

    rep.overall = (
        f"【综合】{verdict}（互补分 {rep.complement_score}）。"
        f"{rep.chemistry}。"
        f"{'共同短板：' + '/'.join(rep.common_lacking) + '。' if rep.common_lacking else ''}"
    )

    return rep


def render_compat(rep: CompatReport) -> str:
    """合盘报告的人类可读版"""
    lines = []
    lines.append("━━━━━━ 合盘分析 ━━━━━━")
    lines.append(f"  {rep.person_a_name}: {rep.summary_a}")
    lines.append(f"  {rep.person_b_name}: {rep.summary_b}")
    lines.append("")
    lines.append(f"【日主关系】{rep.rizhu_relation}")
    lines.append(f"  {rep.rizhu_explain}")
    lines.append("")
    lines.append("【五行互补】")
    for wx, desc in rep.wuxing_complement.items():
        lines.append(f"  {wx}: {desc}")
    lines.append("")
    lines.append(f"【化学反应】{rep.chemistry}")
    if rep.pros:
        lines.append("【优势】")
        for p in rep.pros:
            lines.append(f"  ✓ {p}")
    if rep.cons:
        lines.append("【需要注意】")
        for c in rep.cons:
            lines.append(f"  ⚠ {c}")
    lines.append("")
    lines.append(f"【建议】{rep.advice}")
    lines.append("")
    lines.append(rep.overall)
    return "\n".join(lines)


if __name__ == "__main__":
    from .bazi import build_bazi
    a = build_bazi(2000, 7, 10, hour=12, gender="男", name="你")
    b = build_bazi(2002, 6, 18, hour=12, gender="女", name="TA")
    rep = analyze_compat(a, b, "你", "TA")
    print(render_compat(rep))
