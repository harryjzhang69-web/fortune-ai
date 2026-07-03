"""
fortune_ai 后端 API（FastAPI）
为微信小程序 / H5 / 任意前端提供 HTTP 接口。

跑法：
    cd fortune_ai
    uvicorn server.app:app --reload --port 8000

接口：
    GET  /                          健康检查
    POST /api/bazi                  排八字
    POST /api/yijing/divine         易经起卦
    POST /api/compat                合盘
    POST /api/chat                  AI 对话（非流式）
    POST /api/chat/stream           AI 对话（SSE 流式）
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional, Literal
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core import (
    build_bazi, render_chart_text,
    divine_by_coins, divine_by_numbers, divine_by_time, render_divination,
    analyze_compat, render_compat,
)
from ai import FortuneChat


app = FastAPI(
    title="命由我造 · Fortune AI",
    description="基于易经、八字的传统文化体验 API",
    version="0.1.0",
)

# CORS：开发期全开，上线收紧
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 请求 / 响应模型 =====

class BirthInfo(BaseModel):
    year: int = Field(..., ge=1900, le=2100, description="公历年")
    month: int = Field(..., ge=1, le=12)
    day: int = Field(..., ge=1, le=31)
    hour: Optional[int] = Field(None, ge=0, le=23, description="出生小时；None 表示未知")
    minute: int = Field(0, ge=0, le=59)
    gender: Literal["男", "女", "未知"] = "未知"
    name: Optional[str] = None
    is_lunar: bool = False


class BaziResponse(BaseModel):
    summary: str
    chart_text: str
    raw: dict


class DivineRequest(BaseModel):
    method: Literal["coins", "numbers", "time"] = "coins"
    question: str = ""
    numbers: Optional[list[int]] = None  # method=numbers 时使用


class DivineResponse(BaseModel):
    summary: str
    text: str
    raw: dict


class CompatRequest(BaseModel):
    person_a: BirthInfo
    person_b: BirthInfo
    name_a: str = "你"
    name_b: str = "TA"


class CompatResponse(BaseModel):
    text: str
    score: int
    raw: dict


class ChatRequest(BaseModel):
    question: str
    history: list[dict] = []
    # 上下文（任选）
    user_chart_full: Optional[str] = None
    partner_chart_full: Optional[str] = None
    compat_report: Optional[str] = None
    divination_full: Optional[str] = None
    mode: Literal["auto", "bazi", "yijing", "compat"] = "auto"


# ===== 路由 =====

@app.get("/")
def root():
    return {
        "app": "命由我造 · Fortune AI",
        "version": "0.1.0",
        "endpoints": [
            "POST /api/bazi",
            "POST /api/yijing/divine",
            "POST /api/compat",
            "POST /api/chat",
            "POST /api/chat/stream",
        ],
    }


@app.post("/api/bazi", response_model=BaziResponse)
def api_bazi(info: BirthInfo):
    try:
        chart = build_bazi(
            year=info.year, month=info.month, day=info.day,
            hour=info.hour, minute=info.minute,
            gender=info.gender, name=info.name, is_lunar=info.is_lunar,
        )
    except Exception as e:
        raise HTTPException(400, f"排盘失败：{e}")
    return BaziResponse(
        summary=chart.summary(),
        chart_text=render_chart_text(chart),
        raw={
            "year": chart.year.__dict__, "month": chart.month.__dict__,
            "day": chart.day.__dict__,
            "hour": chart.hour.__dict__ if chart.hour else None,
            "rizhu": chart.rizhu, "rizhu_wuxing": chart.rizhu_wuxing,
            "rizhu_yinyang": chart.rizhu_yinyang,
            "wuxing_dist": chart.wuxing_dist.to_dict(),
            "wuxing_lacking": chart.wuxing_lacking,
            "wuxing_strongest": chart.wuxing_strongest,
            "shishen": chart.shishen,
            "dayun": chart.dayun_list,
            "current_dayun": chart.current_dayun,
            "current_year_ganzhi": chart.current_year_ganzhi,
        },
    )


@app.post("/api/yijing/divine", response_model=DivineResponse)
def api_divine(req: DivineRequest):
    try:
        if req.method == "coins":
            r = divine_by_coins(question=req.question)
        elif req.method == "numbers":
            if not req.numbers or len(req.numbers) < 3:
                raise HTTPException(400, "method=numbers 时必须提供 numbers（至少 3 个数字）")
            r = divine_by_numbers(req.numbers[0], req.numbers[1], req.numbers[2],
                                   question=req.question)
        else:
            r = divine_by_time(question=req.question)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"起卦失败：{e}")

    raw = {
        "method": r.method, "question": r.question,
        "timestamp": r.timestamp,
        "main_gua": {
            "name": r.main_gua.name, "symbol": r.main_gua.symbol,
            "no": r.main_gua.no,
            "yaos": [{"position": y.position, "is_yang": y.is_yang,
                      "is_changing": y.is_changing, "text": y.text}
                     for y in r.main_gua.yaos],
            "judgment": r.main_gua.judgment,
            "image": r.main_gua.image,
            "interp": r.main_gua.interp,
            "keywords": r.main_gua.keywords,
        },
        "changing_yaos": r.changing_yaos,
        "changed_gua": ({
            "name": r.changed_gua.name, "symbol": r.changed_gua.symbol,
            "no": r.changed_gua.no,
            "interp": r.changed_gua.interp,
        } if r.changed_gua else None),
    }
    return DivineResponse(
        summary=r.summary(),
        text=render_divination(r),
        raw=raw,
    )


@app.post("/api/compat", response_model=CompatResponse)
def api_compat(req: CompatRequest):
    try:
        ca = build_bazi(
            year=req.person_a.year, month=req.person_a.month, day=req.person_a.day,
            hour=req.person_a.hour, minute=req.person_a.minute,
            gender=req.person_a.gender, name=req.name_a,
        )
        cb = build_bazi(
            year=req.person_b.year, month=req.person_b.month, day=req.person_b.day,
            hour=req.person_b.hour, minute=req.person_b.minute,
            gender=req.person_b.gender, name=req.name_b,
        )
        rep = analyze_compat(ca, cb, name_a=req.name_a, name_b=req.name_b)
    except Exception as e:
        raise HTTPException(400, f"合盘失败：{e}")
    return CompatResponse(
        text=render_compat(rep),
        score=rep.complement_score,
        raw={
            "rizhu_relation": rep.rizhu_relation,
            "rizhu_explain": rep.rizhu_explain,
            "wuxing_complement": rep.wuxing_complement,
            "common_lacking": rep.common_lacking,
            "chemistry": rep.chemistry,
            "pros": rep.pros, "cons": rep.cons,
            "advice": rep.advice, "overall": rep.overall,
        },
    )


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    chat = FortuneChat(mode=req.mode)
    chat.history = req.history.copy()
    chat.set_context(
        user_chart_full=req.user_chart_full,
        partner_chart_full=req.partner_chart_full,
        compat_report=req.compat_report,
        divination_full=req.divination_full,
        user_question=req.question,
    )
    answer = chat.chat(req.question)
    return {"answer": answer, "history": chat.history}


@app.post("/api/chat/stream")
def api_chat_stream(req: ChatRequest):
    chat = FortuneChat(mode=req.mode)
    chat.history = req.history.copy()
    chat.set_context(
        user_chart_full=req.user_chart_full,
        partner_chart_full=req.partner_chart_full,
        compat_report=req.compat_report,
        divination_full=req.divination_full,
        user_question=req.question,
    )

    def gen():
        try:
            for chunk in chat.chat_stream(req.question):
                # SSE 格式
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
