"""
八字排盘引擎
基于 lunar-python，输入公历生日 → 输出完整命盘信息

核心输出：
- 四柱（年月日时）干支
- 日主（命主）
- 五行分布与旺衰
- 十神
- 大运（10年运）
- 当前流年
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime

try:
    from lunar_python import Solar, Lunar
except ImportError:
    Solar = None
    Lunar = None


# ===== 静态数据 =====

# 天干五行
GAN_WUXING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

# 天干阴阳
GAN_YINYANG = {
    "甲": "阳", "丙": "阳", "戊": "阳", "庚": "阳", "壬": "阳",
    "乙": "阴", "丁": "阴", "己": "阴", "辛": "阴", "癸": "阴",
}

# 地支五行（地支主气）
ZHI_WUXING = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木",
    "辰": "土", "巳": "火", "午": "火", "未": "土",
    "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

# 地支藏干（用于更精确的五行计算）
ZHI_CANG_GAN = {
    "子": ["癸"],
    "丑": ["己", "癸", "辛"],
    "寅": ["甲", "丙", "戊"],
    "卯": ["乙"],
    "辰": ["戊", "乙", "癸"],
    "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"],
    "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"],
    "酉": ["辛"],
    "戌": ["戊", "辛", "丁"],
    "亥": ["壬", "甲"],
}

# 十神映射（以日主天干 → 其他天干的关系）
# 比肩 / 劫财 / 食神 / 伤官 / 偏财 / 正财 / 七杀 / 正官 / 偏印 / 正印
SHISHEN_MAP = {
    # 日主：甲（阳木）
    "甲": {"甲": "比肩", "乙": "劫财", "丙": "食神", "丁": "伤官",
           "戊": "偏财", "己": "正财", "庚": "七杀", "辛": "正官",
           "壬": "偏印", "癸": "正印"},
    "乙": {"甲": "劫财", "乙": "比肩", "丙": "伤官", "丁": "食神",
           "戊": "正财", "己": "偏财", "庚": "正官", "辛": "七杀",
           "壬": "正印", "癸": "偏印"},
    "丙": {"甲": "偏印", "乙": "正印", "丙": "比肩", "丁": "劫财",
           "戊": "食神", "己": "伤官", "庚": "偏财", "辛": "正财",
           "壬": "七杀", "癸": "正官"},
    "丁": {"甲": "正印", "乙": "偏印", "丙": "劫财", "丁": "比肩",
           "戊": "伤官", "己": "食神", "庚": "正财", "辛": "偏财",
           "壬": "正官", "癸": "七杀"},
    "戊": {"甲": "七杀", "乙": "正官", "丙": "偏印", "丁": "正印",
           "戊": "比肩", "己": "劫财", "庚": "食神", "辛": "伤官",
           "壬": "偏财", "癸": "正财"},
    "己": {"甲": "正官", "乙": "七杀", "丙": "正印", "丁": "偏印",
           "戊": "劫财", "己": "比肩", "庚": "伤官", "辛": "食神",
           "壬": "正财", "癸": "偏财"},
    "庚": {"甲": "偏财", "乙": "正财", "丙": "七杀", "丁": "正官",
           "戊": "偏印", "己": "正印", "庚": "比肩", "辛": "劫财",
           "壬": "食神", "癸": "伤官"},
    "辛": {"甲": "正财", "乙": "偏财", "丙": "正官", "丁": "七杀",
           "戊": "正印", "己": "偏印", "庚": "劫财", "辛": "比肩",
           "壬": "伤官", "癸": "食神"},
    "壬": {"甲": "食神", "乙": "伤官", "丙": "偏财", "丁": "正财",
           "戊": "七杀", "己": "正官", "庚": "偏印", "辛": "正印",
           "壬": "比肩", "癸": "劫财"},
    "癸": {"甲": "伤官", "乙": "食神", "丙": "正财", "丁": "偏财",
           "戊": "正官", "己": "七杀", "庚": "正印", "辛": "偏印",
           "壬": "劫财", "癸": "比肩"},
}

# 天干意象（用于解读时润色）
GAN_IMAGE = {
    "甲": "参天大树、栋梁",
    "乙": "花草藤蔓、柔木",
    "丙": "太阳、烈火",
    "丁": "烛火、灯火",
    "戊": "高山、厚土",
    "己": "田园、平原",
    "庚": "顽铁、刀剑",
    "辛": "珠玉、首饰",
    "壬": "江河、大海",
    "癸": "雨露、溪水",
}

# 日主性格速写
RIZHU_TRAITS = {
    "甲": "阳木——领导力、有担当、刚直、有时太硬",
    "乙": "阴木——柔韧、有审美、善变通、有时多虑",
    "丙": "阳火——热情、外向、阳光、有时浮躁",
    "丁": "阴火——温柔、感性、细腻、内心有韧性",
    "戊": "阳土——稳重、可靠、固执、节奏慢",
    "己": "阴土——包容、随和、滋养他人、易委屈",
    "庚": "阳金——果断、刚强、讲义气、易冲动",
    "辛": "阴金——精致、敏感、要面子、外柔内硬",
    "壬": "阳水——聪明、外向、流动、易飘",
    "癸": "阴水——智慧、含蓄、敏感、心思深",
}


@dataclass
class Pillar:
    """单柱（年/月/日/时）"""
    gan: str            # 天干
    zhi: str            # 地支
    gan_wuxing: str     # 天干五行
    zhi_wuxing: str     # 地支主气五行

    @property
    def name(self) -> str:
        return f"{self.gan}{self.zhi}"


@dataclass
class WuxingDist:
    """五行分布"""
    jin: int = 0   # 金
    mu: int = 0    # 木
    shui: int = 0  # 水
    huo: int = 0   # 火
    tu: int = 0    # 土

    def total(self) -> int:
        return self.jin + self.mu + self.shui + self.huo + self.tu

    def to_dict(self) -> dict:
        return {"金": self.jin, "木": self.mu, "水": self.shui,
                "火": self.huo, "土": self.tu}

    def lacking(self) -> list[str]:
        """返回缺失的五行（计数为0）"""
        d = self.to_dict()
        return [k for k, v in d.items() if v == 0]

    def strongest(self) -> list[str]:
        """返回最旺的五行"""
        d = self.to_dict()
        max_val = max(d.values())
        if max_val == 0:
            return []
        return [k for k, v in d.items() if v == max_val]


@dataclass
class BaziChart:
    """完整八字命盘"""
    # 基本信息
    name: Optional[str] = None
    gender: str = "未知"  # 男/女/未知
    solar_date: str = ""  # 公历 yyyy-mm-dd HH:MM
    lunar_date: str = ""  # 农历

    # 四柱
    year: Pillar = None
    month: Pillar = None
    day: Pillar = None      # 日柱（日干即"日主"）
    hour: Optional[Pillar] = None  # 时柱（可空）
    has_hour: bool = True

    # 派生信息
    rizhu: str = ""             # 日主天干
    rizhu_wuxing: str = ""      # 日主五行
    rizhu_yinyang: str = ""     # 日主阴阳
    rizhu_image: str = ""       # 日主意象
    rizhu_traits: str = ""      # 日主性格速写
    wuxing_dist: WuxingDist = field(default_factory=WuxingDist)
    wuxing_lacking: list[str] = field(default_factory=list)
    wuxing_strongest: list[str] = field(default_factory=list)
    shishen: dict = field(default_factory=dict)  # 各柱十神

    # 大运 / 流年
    dayun_list: list[dict] = field(default_factory=list)  # 大运列表
    current_dayun: Optional[dict] = None
    current_year_ganzhi: str = ""  # 今年干支

    def to_dict(self) -> dict:
        d = asdict(self)
        # 处理 Pillar 里的不可序列化情况
        return d

    def summary(self) -> str:
        """一句话摘要，给 AI 用"""
        pillars = f"{self.year.name} {self.month.name} {self.day.name}"
        if self.has_hour and self.hour:
            pillars += f" {self.hour.name}"
        return (
            f"{self.solar_date}（{self.lunar_date}），"
            f"四柱：{pillars}；"
            f"日主：{self.rizhu}（{self.rizhu_yinyang}{self.rizhu_wuxing}，{self.rizhu_image}）；"
            f"五行分布：{self.wuxing_dist.to_dict()}，"
            f"缺：{self.wuxing_lacking or '无'}，"
            f"最旺：{self.wuxing_strongest}"
        )


def _count_wuxing(pillars: list[Pillar], use_canggan: bool = True) -> WuxingDist:
    """统计五行分布。
    use_canggan=True 时计入地支藏干（更精细）；
    False 时只计天干 + 地支主气（更直观）。
    """
    dist = WuxingDist()
    name_to_attr = {"金": "jin", "木": "mu", "水": "shui", "火": "huo", "土": "tu"}

    for p in pillars:
        if p is None:
            continue
        # 天干
        wx = GAN_WUXING.get(p.gan)
        if wx:
            setattr(dist, name_to_attr[wx], getattr(dist, name_to_attr[wx]) + 1)
        # 地支主气
        wx = ZHI_WUXING.get(p.zhi)
        if wx:
            setattr(dist, name_to_attr[wx], getattr(dist, name_to_attr[wx]) + 1)
        # 地支藏干（次气，权重折半，简化为 +1 的一半 = 不加，仅做参考）
        # 这里采取简化方案：只统计主气，避免新人看不懂"为什么 4+3+5=12 不是 8"
        # 如需精细模式，把下面注释打开
        # if use_canggan:
        #     for cg in ZHI_CANG_GAN.get(p.zhi, [])[1:]:  # 跳过主气
        #         wx = GAN_WUXING.get(cg)
        #         if wx:
        #             setattr(dist, name_to_attr[wx], getattr(dist, name_to_attr[wx]) + 0.5)
    return dist


def build_bazi(
    year: int, month: int, day: int,
    hour: Optional[int] = None, minute: int = 0,
    gender: str = "未知",
    name: Optional[str] = None,
    is_lunar: bool = False,
) -> BaziChart:
    """
    构建八字命盘。

    Args:
        year/month/day: 公历日期（默认）或农历日期（is_lunar=True）
        hour: 0-23，None 表示不知道时辰
        gender: '男'/'女'/'未知'
        is_lunar: 输入是否为农历

    Returns:
        BaziChart
    """
    if Solar is None:
        raise ImportError("请先安装 lunar-python: pip install lunar-python")

    has_hour = hour is not None
    h = hour if has_hour else 12   # 没时辰时用12点占位（不用于时柱输出）

    if is_lunar:
        lunar = Lunar.fromYmdHms(year, month, day, h, minute, 0)
        solar = lunar.getSolar()
    else:
        solar = Solar.fromYmdHms(year, month, day, h, minute, 0)
        lunar = solar.getLunar()

    eight_char = lunar.getEightChar()

    # 四柱
    y = Pillar(
        gan=eight_char.getYearGan(),
        zhi=eight_char.getYearZhi(),
        gan_wuxing=GAN_WUXING.get(eight_char.getYearGan(), ""),
        zhi_wuxing=ZHI_WUXING.get(eight_char.getYearZhi(), ""),
    )
    m = Pillar(
        gan=eight_char.getMonthGan(),
        zhi=eight_char.getMonthZhi(),
        gan_wuxing=GAN_WUXING.get(eight_char.getMonthGan(), ""),
        zhi_wuxing=ZHI_WUXING.get(eight_char.getMonthZhi(), ""),
    )
    d = Pillar(
        gan=eight_char.getDayGan(),
        zhi=eight_char.getDayZhi(),
        gan_wuxing=GAN_WUXING.get(eight_char.getDayGan(), ""),
        zhi_wuxing=ZHI_WUXING.get(eight_char.getDayZhi(), ""),
    )

    if has_hour:
        t = Pillar(
            gan=eight_char.getTimeGan(),
            zhi=eight_char.getTimeZhi(),
            gan_wuxing=GAN_WUXING.get(eight_char.getTimeGan(), ""),
            zhi_wuxing=ZHI_WUXING.get(eight_char.getTimeZhi(), ""),
        )
    else:
        t = None

    pillars = [y, m, d] + ([t] if t else [])

    # 五行分布
    dist = _count_wuxing(pillars)

    # 日主信息
    rizhu = d.gan
    rizhu_wuxing = GAN_WUXING.get(rizhu, "")
    rizhu_yinyang = GAN_YINYANG.get(rizhu, "")
    rizhu_image = GAN_IMAGE.get(rizhu, "")
    rizhu_traits = RIZHU_TRAITS.get(rizhu, "")

    # 十神（以日主为基准，看其他柱天干）
    shishen_table = SHISHEN_MAP.get(rizhu, {})
    shishen = {
        "年干": shishen_table.get(y.gan, ""),
        "月干": shishen_table.get(m.gan, ""),
    }
    if t:
        shishen["时干"] = shishen_table.get(t.gan, "")

    # 大运
    dayun_list = []
    current_dayun = None
    try:
        # gender: 1=男 0=女
        gender_code = 1 if gender == "男" else (0 if gender == "女" else 1)
        yun = eight_char.getYun(gender_code)
        # 取前 8 步大运
        dayun_arr = yun.getDaYun()
        now = datetime.now()
        for i in range(min(9, len(dayun_arr))):
            dy = dayun_arr[i]
            start_year = dy.getStartYear()
            end_year = dy.getEndYear() if hasattr(dy, "getEndYear") else (start_year + 9)
            start_age = dy.getStartAge() if hasattr(dy, "getStartAge") else 0
            ganzhi = dy.getGanZhi() if hasattr(dy, "getGanZhi") else ""
            entry = {
                "index": i,
                "ganzhi": ganzhi,
                "start_year": start_year,
                "end_year": end_year,
                "start_age": start_age,
            }
            dayun_list.append(entry)
            if start_year <= now.year <= end_year and i > 0:
                # i==0 是起运前，跳过
                current_dayun = entry
    except Exception as e:
        # 没时辰算不出大运，跳过
        pass

    # 当年干支
    current_year_ganzhi = ""
    try:
        cur_solar = Solar.fromDate(datetime.now())
        current_year_ganzhi = cur_solar.getLunar().getYearInGanZhi()
    except Exception:
        pass

    chart = BaziChart(
        name=name,
        gender=gender,
        solar_date=f"{year:04d}-{month:02d}-{day:02d}" + (f" {hour:02d}:{minute:02d}" if has_hour else ""),
        lunar_date=f"{lunar.getYearInGanZhi()}年 {lunar.getMonthInChinese()}月 {lunar.getDayInChinese()}",
        year=y, month=m, day=d, hour=t,
        has_hour=has_hour,
        rizhu=rizhu,
        rizhu_wuxing=rizhu_wuxing,
        rizhu_yinyang=rizhu_yinyang,
        rizhu_image=rizhu_image,
        rizhu_traits=rizhu_traits,
        wuxing_dist=dist,
        wuxing_lacking=dist.lacking(),
        wuxing_strongest=dist.strongest(),
        shishen=shishen,
        dayun_list=dayun_list,
        current_dayun=current_dayun,
        current_year_ganzhi=current_year_ganzhi,
    )
    return chart


def render_chart_text(chart: BaziChart) -> str:
    """命盘的人类可读文字版（用于 CLI 展示 / AI 上下文注入）"""
    lines = []
    lines.append(f"📅 公历：{chart.solar_date}")
    lines.append(f"🌙 农历：{chart.lunar_date}")
    lines.append(f"🚻 性别：{chart.gender}")
    lines.append("")
    lines.append("【四柱】")
    head = f"  年柱: {chart.year.name}  月柱: {chart.month.name}  日柱: {chart.day.name}"
    if chart.has_hour and chart.hour:
        head += f"  时柱: {chart.hour.name}"
    else:
        head += "  时柱: ?(未提供时辰)"
    lines.append(head)
    lines.append("")
    lines.append(f"【日主】{chart.rizhu}（{chart.rizhu_yinyang}{chart.rizhu_wuxing}）")
    lines.append(f"  意象：{chart.rizhu_image}")
    lines.append(f"  性格速写：{chart.rizhu_traits}")
    lines.append("")
    lines.append("【五行分布】")
    d = chart.wuxing_dist.to_dict()
    bar = "  " + "  ".join(f"{k}:{v}" for k, v in d.items())
    lines.append(bar)
    if chart.wuxing_lacking:
        lines.append(f"  ⚠️ 缺：{'/'.join(chart.wuxing_lacking)}")
    if chart.wuxing_strongest:
        lines.append(f"  💪 最旺：{'/'.join(chart.wuxing_strongest)}")
    lines.append("")
    if chart.shishen:
        lines.append("【十神】")
        lines.append("  " + "  ".join(f"{k}={v}" for k, v in chart.shishen.items()))
        lines.append("")
    if chart.dayun_list:
        lines.append("【大运】（10年一步）")
        for dy in chart.dayun_list[:8]:
            mark = " ← 当前" if chart.current_dayun and dy["index"] == chart.current_dayun["index"] else ""
            lines.append(f"  {dy['ganzhi']}  {dy['start_year']}-{dy['end_year']}  ({dy['start_age']}岁起){mark}")
        lines.append("")
    if chart.current_year_ganzhi:
        lines.append(f"【今年流年】{chart.current_year_ganzhi}")
    return "\n".join(lines)


if __name__ == "__main__":
    # 自测：用我们之前聊的那个例子
    chart = build_bazi(2000, 7, 10, hour=12, gender="男", name="测试用户A")
    print(render_chart_text(chart))
    print()
    print("=" * 50)
    print("摘要：", chart.summary())
