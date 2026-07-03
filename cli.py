"""
fortune_ai · CLI Demo
完整体验：八字 + 易经 + 合盘 + AI 对话

跑法：
    python cli.py
"""
from __future__ import annotations
import sys
from datetime import datetime
from pathlib import Path

# 让 cli.py 在 fortune_ai 目录直接跑
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.markdown import Markdown
from rich.text import Text
from rich import box

from core import (
    build_bazi, render_chart_text,
    divine_by_coins, divine_by_numbers, divine_by_time, render_divination,
    analyze_compat, render_compat,
)
from ai import FortuneChat, DISCLAIMER_FOOTER

console = Console()


# ===== UI helpers =====

def title():
    console.print(Panel(
        Text("🔮  命由我造 · 玄镜 AI 命理师  🔮", justify="center", style="bold magenta"),
        subtitle="[dim]易经 · 八字 · 合盘 · AI 陪伴[/dim]",
        box=box.DOUBLE_EDGE,
    ))
    console.print(
        "[dim]⚠️ 本工具为传统文化娱乐性质，不是科学预测，不构成任何决策建议。[/dim]\n"
    )


def menu_main() -> str:
    console.print(Panel(
        "[bold]请选择体验方式：[/bold]\n"
        "  [cyan]1[/cyan]. 排我的八字命盘 + AI 解读\n"
        "  [cyan]2[/cyan]. 易经起卦（问一件具体事）\n"
        "  [cyan]3[/cyan]. 双人合盘（我和 TA 的关系）\n"
        "  [cyan]4[/cyan]. 综合模式（命盘+合盘+起卦，AI 全部联动）\n"
        "  [cyan]q[/cyan]. 退出",
        title="主菜单", border_style="cyan",
    ))
    return Prompt.ask("[bold cyan]选择[/bold cyan]", choices=["1", "2", "3", "4", "q"], default="4")


def input_birth(prompt_name: str = "你") -> dict:
    console.print(f"\n[bold yellow]━━━ 录入「{prompt_name}」的出生信息 ━━━[/bold yellow]")
    while True:
        s = Prompt.ask(f"  {prompt_name}的出生日期（公历，格式 YYYY-MM-DD，如 2000-07-10）")
        try:
            year, month, day = map(int, s.split("-"))
            datetime(year, month, day)  # 验证
            break
        except Exception:
            console.print("[red]  日期格式不对，请重试[/red]")

    has_hour = Confirm.ask(f"  是否知道{prompt_name}的具体出生时间？", default=False)
    hour = None
    minute = 0
    if has_hour:
        hour = IntPrompt.ask(f"  出生小时（0-23）", default=12)
        minute = IntPrompt.ask(f"  出生分钟（0-59）", default=0)

    gender = Prompt.ask(f"  {prompt_name}的性别", choices=["男", "女", "未知"], default="未知")

    return {
        "year": year, "month": month, "day": day,
        "hour": hour, "minute": minute,
        "gender": gender, "name": prompt_name,
    }


# ===== 模式实现 =====

def mode_bazi():
    info = input_birth("你")
    chart = build_bazi(**info)
    console.print()
    console.print(Panel(render_chart_text(chart), title="八字命盘", border_style="green"))

    if not Confirm.ask("\n[cyan]接下来用 AI 解读？[/cyan]", default=True):
        return

    chat = FortuneChat(mode="bazi")
    chat.set_context(user_chart_full=render_chart_text(chart))

    _interactive_chat(chat, intro="给你简单解读一下这个盘，然后我们随便聊。")


def mode_yijing():
    console.print("\n[bold yellow]━━━ 易经起卦 ━━━[/bold yellow]")
    question = Prompt.ask("  你想问什么？（具体一件事，比如：'要不要换工作'）")

    way = Prompt.ask(
        "  起卦方式：[cyan]1[/cyan]模拟摇卦  [cyan]2[/cyan]报数起卦  [cyan]3[/cyan]时间起卦",
        choices=["1", "2", "3"], default="1",
    )

    console.print()
    if way == "1":
        result = divine_by_coins(question=question)
    elif way == "2":
        n1 = IntPrompt.ask("  第一个数（任意正整数）")
        n2 = IntPrompt.ask("  第二个数")
        n3 = IntPrompt.ask("  第三个数")
        result = divine_by_numbers(n1, n2, n3, question=question)
    else:
        result = divine_by_time(question=question)

    console.print(Panel(render_divination(result), title="卦象", border_style="green"))

    if not Confirm.ask("\n[cyan]接下来用 AI 解读？[/cyan]", default=True):
        return

    chat = FortuneChat(mode="yijing")
    chat.set_context(divination_full=render_divination(result), user_question=question)

    _interactive_chat(chat, intro="结合这个卦，回答你的问题。")


def mode_compat():
    info_a = input_birth("你")
    info_b = input_birth("TA")
    chart_a = build_bazi(**info_a)
    chart_b = build_bazi(**info_b)
    rep = analyze_compat(chart_a, chart_b, name_a="你", name_b="TA")
    console.print()
    console.print(Panel(render_compat(rep), title="合盘分析", border_style="green"))

    if not Confirm.ask("\n[cyan]接下来用 AI 解读？[/cyan]", default=True):
        return

    chat = FortuneChat(mode="compat")
    chat.set_context(
        user_chart_full=render_chart_text(chart_a),
        partner_chart_full=render_chart_text(chart_b),
        compat_report=render_compat(rep),
    )

    _interactive_chat(chat, intro="先简单点评这段关系，然后你想问什么都可以。")


def mode_combo():
    """综合模式：命盘 + 合盘 + 起卦 + AI 全部联动（最完整体验）"""
    console.print("\n[bold magenta]🌟 综合模式：完整体验「双盘互证」[/bold magenta]")

    info_a = input_birth("你")
    chart_a = build_bazi(**info_a)

    has_partner = Confirm.ask("\n  要不要再录入对方的信息（合盘）？", default=True)
    chart_b = None
    rep = None
    if has_partner:
        info_b = input_birth("TA")
        chart_b = build_bazi(**info_b)
        rep = analyze_compat(chart_a, chart_b, name_a="你", name_b="TA")

    question = Prompt.ask("\n  你最想问的一件事是？")

    way = Prompt.ask(
        "  起卦方式：[cyan]1[/cyan]模拟摇卦  [cyan]2[/cyan]时间起卦",
        choices=["1", "2"], default="1",
    )
    if way == "1":
        result = divine_by_coins(question=question)
    else:
        result = divine_by_time(question=question)

    # 展示
    console.print()
    console.print(Panel(render_chart_text(chart_a), title="你的八字命盘", border_style="green"))
    if chart_b:
        console.print(Panel(render_chart_text(chart_b), title="TA 的八字命盘", border_style="green"))
        console.print(Panel(render_compat(rep), title="合盘分析", border_style="cyan"))
    console.print(Panel(render_divination(result), title="易经起卦", border_style="yellow"))

    # AI 解读
    chat = FortuneChat(mode="auto")
    ctx = {
        "user_chart_full": render_chart_text(chart_a),
        "divination_full": render_divination(result),
        "user_question": question,
    }
    if chart_b:
        ctx["partner_chart_full"] = render_chart_text(chart_b)
        ctx["compat_report"] = render_compat(rep)
    chat.set_context(**ctx)

    _interactive_chat(chat, intro=f"基于你的命盘+合盘+卦象，回答你的问题：「{question}」。请双盘互证地解读。")


# ===== 交互式对话 =====

def _interactive_chat(chat: FortuneChat, intro: str = ""):
    console.print()
    console.print(Panel(
        f"[bold cyan]🪞 玄镜[/bold cyan]：开始解读了。你随时可以追问、换话题。\n"
        f"[dim](输入 'q' 退出本次对话；'reset' 清空历史)[/dim]",
        border_style="magenta",
    ))

    # 第一轮：让 AI 主动开聊
    console.print("[dim]  正在生成解读...[/dim]\n")
    console.print("[bold magenta]🪞 玄镜：[/bold magenta]", end="")
    try:
        for chunk in chat.chat_stream(intro):
            console.print(chunk, end="", style="white")
    except Exception as e:
        console.print(f"[red]\n  ❌ 出错了：{e}[/red]")
        return
    console.print(f"\n[dim]{DISCLAIMER_FOOTER.strip()}[/dim]")

    # 后续追问
    while True:
        console.print()
        q = Prompt.ask("[bold cyan]你[/bold cyan]")
        if q.strip().lower() in ("q", "quit", "exit"):
            break
        if q.strip().lower() == "reset":
            chat.reset()
            console.print("[yellow]  历史已清空。[/yellow]")
            continue
        console.print()
        console.print("[bold magenta]🪞 玄镜：[/bold magenta]", end="")
        try:
            for chunk in chat.chat_stream(q):
                console.print(chunk, end="", style="white")
            console.print()
        except Exception as e:
            console.print(f"[red]\n  ❌ 出错了：{e}[/red]")
            break


# ===== 主入口 =====

def main():
    title()
    while True:
        choice = menu_main()
        if choice == "q":
            console.print("\n[dim]再见～[/dim]")
            break
        try:
            if choice == "1":
                mode_bazi()
            elif choice == "2":
                mode_yijing()
            elif choice == "3":
                mode_compat()
            elif choice == "4":
                mode_combo()
        except KeyboardInterrupt:
            console.print("\n[dim](中断)[/dim]")
        except Exception as e:
            console.print(f"\n[red]❌ 出错了：{e}[/red]")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
