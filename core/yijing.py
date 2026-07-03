"""
易经起卦引擎
支持三种起卦方式：
  1. 时间起卦（基于当下年月日时）
  2. 报数起卦（用户报3个数字）
  3. 模拟摇卦（电子六爻铜钱法，最常见）

输出本卦 + 变爻 + 之卦 + 卦辞 + 爻辞。
"""
from __future__ import annotations
import os
import json
import random
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
from pathlib import Path


# ===== 静态数据 =====

# 八卦：先天八卦序号（伏羲序）
BAGUA = [
    {"id": 1, "name": "乾", "symbol": "☰", "binary": "111", "wuxing": "金", "image": "天", "nature": "刚健"},
    {"id": 2, "name": "兑", "symbol": "☱", "binary": "011", "wuxing": "金", "image": "泽", "nature": "悦"},
    {"id": 3, "name": "离", "symbol": "☲", "binary": "101", "wuxing": "火", "image": "火", "nature": "丽"},
    {"id": 4, "name": "震", "symbol": "☳", "binary": "001", "wuxing": "木", "image": "雷", "nature": "动"},
    {"id": 5, "name": "巽", "symbol": "☴", "binary": "110", "wuxing": "木", "image": "风", "nature": "入"},
    {"id": 6, "name": "坎", "symbol": "☵", "binary": "010", "wuxing": "水", "image": "水", "nature": "陷"},
    {"id": 7, "name": "艮", "symbol": "☶", "binary": "100", "wuxing": "土", "image": "山", "nature": "止"},
    {"id": 8, "name": "坤", "symbol": "☷", "binary": "000", "wuxing": "土", "image": "地", "nature": "顺"},
]

# binary → 八卦
BAGUA_BY_BIN = {b["binary"]: b for b in BAGUA}
# id → 八卦
BAGUA_BY_ID = {b["id"]: b for b in BAGUA}


@dataclass
class Yao:
    """爻：六爻之一"""
    position: int          # 1-6（初爻=1，上爻=6）
    is_yang: bool          # True=阳爻，False=阴爻
    is_changing: bool = False   # 是否动爻
    text: str = ""         # 爻辞


@dataclass
class Gua:
    """卦：6 爻组成"""
    yaos: list[Yao]                    # 自下而上 [初爻, 二爻, 三爻, 四爻, 五爻, 上爻]
    name: str = ""                     # 卦名（如"天雷无妄"）
    short_name: str = ""               # 短名（如"无妄"）
    symbol: str = ""                   # 卦象符号
    upper: dict = field(default_factory=dict)   # 上卦
    lower: dict = field(default_factory=dict)   # 下卦
    no: int = 0                        # 卦序（1-64）
    judgment: str = ""                 # 卦辞
    image: str = ""                    # 大象辞
    interp: str = ""                   # 简释
    keywords: list[str] = field(default_factory=list)

    def render_lines(self) -> str:
        """渲染卦象（自上而下）"""
        lines = []
        for i in range(5, -1, -1):  # 从上到下
            yao = self.yaos[i]
            mark = " ✕动" if yao.is_changing and yao.is_yang else (
                " ○动" if yao.is_changing and not yao.is_yang else ""
            )
            if yao.is_yang:
                lines.append(f"  {i+1}爻  ▅▅▅▅▅{mark}")
            else:
                lines.append(f"  {i+1}爻  ▅▅ ▅▅{mark}")
        return "\n".join(lines)


@dataclass
class DivinationResult:
    """起卦结果"""
    method: str = ""                # 起卦方式
    question: str = ""              # 问题
    timestamp: str = ""             # 起卦时间
    main_gua: Gua = None            # 本卦
    changed_gua: Optional[Gua] = None    # 之卦（无变爻则为 None）
    changing_yaos: list[int] = field(default_factory=list)  # 动爻位置 1-6

    def summary(self) -> str:
        """给 AI 用的摘要"""
        if not self.main_gua:
            return ""
        s = f"本卦：{self.main_gua.name} ({self.main_gua.symbol})"
        if self.changing_yaos:
            yao_names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
            s += f"，动爻：{','.join(yao_names[i-1] for i in self.changing_yaos)}"
        if self.changed_gua:
            s += f"，之卦：{self.changed_gua.name} ({self.changed_gua.symbol})"
        return s


# ===== 核心算法 =====

def _yaos_to_gua_data(yaos: list[Yao]) -> tuple[dict, dict, str]:
    """6 爻 → (上卦, 下卦, 6位二进制串)。
    yaos 顺序：初爻在前 [初, 二, 三, 四, 五, 上]
    下卦 = 初/二/三爻；上卦 = 四/五/上爻
    八卦内部读法：上为最高位
        下卦二进制 = 三爻 二爻 初爻
        上卦二进制 = 上爻 五爻 四爻
    """
    def to_bit(y: Yao) -> str:
        return "1" if y.is_yang else "0"

    # 下卦：自下而上 yaos[0..2]
    lower_bin = to_bit(yaos[2]) + to_bit(yaos[1]) + to_bit(yaos[0])
    upper_bin = to_bit(yaos[5]) + to_bit(yaos[4]) + to_bit(yaos[3])
    lower = BAGUA_BY_BIN[lower_bin]
    upper = BAGUA_BY_BIN[upper_bin]
    return upper, lower, upper_bin + lower_bin   # 6位串


def _build_gua_from_yaos(yaos: list[Yao], gua_data: dict) -> Gua:
    """从 6 爻和 64 卦数据库构建 Gua"""
    upper, lower, _ = _yaos_to_gua_data(yaos)
    # 用 (upper_id, lower_id) 在 gua64.json 里找
    key = f"{upper['id']}-{lower['id']}"
    info = gua_data.get(key, {})
    name = info.get("name", f"{upper['name']}{lower['name']}")
    short = info.get("short_name", name)
    symbol = upper["symbol"] + lower["symbol"]

    gua = Gua(
        yaos=yaos,
        name=name,
        short_name=short,
        symbol=symbol,
        upper=upper,
        lower=lower,
        no=info.get("no", 0),
        judgment=info.get("judgment", ""),
        image=info.get("image", ""),
        interp=info.get("interp", ""),
        keywords=info.get("keywords", []),
    )
    # 填爻辞
    yao_texts = info.get("yao_texts", [])
    for i, y in enumerate(gua.yaos):
        if i < len(yao_texts):
            y.text = yao_texts[i]
    return gua


def load_gua64() -> dict:
    """加载 64 卦数据（key 格式 "上卦id-下卦id"）"""
    path = Path(__file__).parent / "data" / "gua64.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 转 {key: info} 形式
    return {item["key"]: item for item in data}


# ===== 起卦方式 =====

def divine_by_coins(question: str = "") -> DivinationResult:
    """
    模拟摇卦（电子铜钱法）：
    每爻摇 3 枚铜钱，正面=3，反面=2，三枚之和 → 6/7/8/9
        6 = 老阴（动爻，变阳）
        7 = 少阳（静爻）
        8 = 少阴（静爻）
        9 = 老阳（动爻，变阴）
    """
    yaos = []
    changing = []
    for i in range(6):  # 自下而上
        s = sum(random.choice([2, 3]) for _ in range(3))
        if s == 9:        # 老阳，动
            yaos.append(Yao(position=i+1, is_yang=True, is_changing=True))
            changing.append(i+1)
        elif s == 6:      # 老阴，动
            yaos.append(Yao(position=i+1, is_yang=False, is_changing=True))
            changing.append(i+1)
        elif s == 7:      # 少阳，静
            yaos.append(Yao(position=i+1, is_yang=True, is_changing=False))
        else:             # s == 8 少阴，静
            yaos.append(Yao(position=i+1, is_yang=False, is_changing=False))

    return _finalize(yaos, changing, "模拟摇卦", question)


def divine_by_numbers(n1: int, n2: int, n3: int, question: str = "") -> DivinationResult:
    """
    报数起卦（梅花易数三数法）：
    n1 → 上卦（除以8取余，0按8算）
    n2 → 下卦（除以8取余）
    (n1+n2+n3) → 动爻（除以6取余，0按6算）
    """
    upper_id = (n1 % 8) or 8
    lower_id = (n2 % 8) or 8
    moving_pos = ((n1 + n2 + n3) % 6) or 6

    return _build_from_bagua_ids(upper_id, lower_id, [moving_pos],
                                  method=f"报数起卦 ({n1},{n2},{n3})", question=question)


def divine_by_time(question: str = "", dt: Optional[datetime] = None) -> DivinationResult:
    """
    时间起卦（梅花易数）：
    年支序数 + 月数 + 日数 → 上卦
    年支 + 月 + 日 + 时支序数 → 下卦
    总和 → 动爻
    """
    if dt is None:
        dt = datetime.now()
    # 简化：直接用阳历年月日时
    # 地支序数 0-11
    ydi = dt.year % 12
    n_upper = ydi + dt.month + dt.day
    # 时辰序数 (0-11，每两小时一个时辰，23:00 也算子时)
    hour_zhi = ((dt.hour + 1) // 2) % 12
    n_lower = ydi + dt.month + dt.day + hour_zhi
    n_total = n_lower

    upper_id = (n_upper % 8) or 8
    lower_id = (n_lower % 8) or 8
    moving_pos = (n_total % 6) or 6

    return _build_from_bagua_ids(upper_id, lower_id, [moving_pos],
                                  method=f"时间起卦 ({dt.strftime('%Y-%m-%d %H:%M')})",
                                  question=question)


def _build_from_bagua_ids(upper_id: int, lower_id: int,
                           changing_positions: list[int],
                           method: str, question: str) -> DivinationResult:
    """从八卦id和动爻位置构建结果（用于梅花易数等）"""
    upper = BAGUA_BY_ID[upper_id]
    lower = BAGUA_BY_ID[lower_id]
    # 上卦二进制：高位在上爻
    yaos = []
    # 下卦三爻（初/二/三）
    for i, bit in enumerate(reversed(lower["binary"])):
        is_yang = bit == "1"
        pos = i + 1
        yaos.append(Yao(position=pos, is_yang=is_yang,
                        is_changing=(pos in changing_positions)))
    # 上卦三爻（四/五/上）
    for i, bit in enumerate(reversed(upper["binary"])):
        is_yang = bit == "1"
        pos = i + 4
        yaos.append(Yao(position=pos, is_yang=is_yang,
                        is_changing=(pos in changing_positions)))
    return _finalize(yaos, list(changing_positions), method, question)


def _finalize(yaos: list[Yao], changing: list[int], method: str, question: str) -> DivinationResult:
    """完成卦构建（本卦+之卦）"""
    gua_data = load_gua64()

    main_gua = _build_gua_from_yaos(yaos, gua_data)

    changed_gua = None
    if changing:
        # 翻转动爻 → 之卦
        new_yaos = []
        for y in yaos:
            if y.is_changing:
                new_yaos.append(Yao(position=y.position,
                                     is_yang=not y.is_yang,
                                     is_changing=False))
            else:
                new_yaos.append(Yao(position=y.position,
                                     is_yang=y.is_yang,
                                     is_changing=False))
        changed_gua = _build_gua_from_yaos(new_yaos, gua_data)

    return DivinationResult(
        method=method,
        question=question,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        main_gua=main_gua,
        changed_gua=changed_gua,
        changing_yaos=changing,
    )


def render_divination(result: DivinationResult) -> str:
    """文字版渲染（CLI 展示 / AI 注入）"""
    lines = []
    lines.append(f"🪙 起卦方式：{result.method}")
    if result.question:
        lines.append(f"❓ 问题：{result.question}")
    lines.append(f"⏰ 时间：{result.timestamp}")
    lines.append("")
    lines.append(f"━━━━━━ 本卦 ━━━━━━")
    g = result.main_gua
    lines.append(f"  {g.name} ({g.symbol})  上{g.upper['name']}({g.upper['image']})/下{g.lower['name']}({g.lower['image']})")
    lines.append(g.render_lines())
    if g.judgment:
        lines.append(f"  📜 卦辞：{g.judgment}")
    if g.image:
        lines.append(f"  🪞 大象：{g.image}")
    if g.interp:
        lines.append(f"  💡 简释：{g.interp}")

    if result.changing_yaos:
        lines.append("")
        lines.append("━━━━━━ 动爻 ━━━━━━")
        yao_names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
        for pos in result.changing_yaos:
            yao = result.main_gua.yaos[pos-1]
            lines.append(f"  {yao_names[pos-1]}：{yao.text or '(待补)'}")

    if result.changed_gua:
        lines.append("")
        lines.append(f"━━━━━━ 之卦 ━━━━━━")
        cg = result.changed_gua
        lines.append(f"  {cg.name} ({cg.symbol})")
        if cg.interp:
            lines.append(f"  💡 简释：{cg.interp}")

    return "\n".join(lines)


if __name__ == "__main__":
    # 自测
    r = divine_by_coins(question="测试用：今天会顺利吗")
    print(render_divination(r))
    print()
    print("摘要：", r.summary())
