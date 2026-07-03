"""
大模型对话封装：兼容 OpenAI 协议（DeepSeek / 通义 / Moonshot / OpenAI）。
支持流式输出。
"""
from __future__ import annotations
import os
from typing import Optional, Iterator, Iterable
from dataclasses import dataclass, field

try:
    from openai import OpenAI
    from openai._exceptions import OpenAIError
except ImportError:
    OpenAI = None
    OpenAIError = Exception

from dotenv import load_dotenv

from .prompts import get_system_prompt, build_user_context, DISCLAIMER_FOOTER


load_dotenv()


@dataclass
class ChatConfig:
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 2000

    @classmethod
    def from_env(cls) -> "ChatConfig":
        return cls(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", ""),
            model=os.getenv("LLM_MODEL", "deepseek-chat"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000")),
        )


class FortuneChat:
    """命理 AI 对话引擎"""

    def __init__(self, config: Optional[ChatConfig] = None, mode: str = "auto"):
        self.config = config or ChatConfig.from_env()
        self.mode = mode
        self.system_prompt = get_system_prompt(mode)
        self.history: list[dict] = []      # 对话历史 [{"role":"...", "content":"..."}]
        self.user_context: str = ""        # 持久的用户上下文（命盘、合盘等）
        self._client = None

    # ---- 上下文管理 ----
    def set_context(self, **kwargs) -> None:
        """设置 / 更新用户的命盘上下文（命盘、合盘、起卦结果都从这里注入）"""
        self.user_context = build_user_context(**kwargs)

    def reset(self) -> None:
        self.history.clear()

    # ---- 客户端 ----
    def _get_client(self):
        if self._client is None:
            if OpenAI is None:
                raise ImportError("请先安装 openai: pip install openai>=1.30.0")
            if not self.config.api_key:
                raise ValueError(
                    "未配置 LLM_API_KEY。请复制 .env.example 为 .env 并填入 API Key。"
                )
            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url or None,
            )
        return self._client

    # ---- 消息构造 ----
    def _build_messages(self, user_input: str, include_context: bool = True) -> list[dict]:
        msgs = [{"role": "system", "content": self.system_prompt}]
        # 用户命盘上下文：作为第一轮 user 消息（只在第一次注入）
        if include_context and self.user_context and not self.history:
            msgs.append({
                "role": "user",
                "content": self.user_context + "\n\n（以上是我的命盘背景。请记住，等会儿我会问问题。）",
            })
            msgs.append({
                "role": "assistant",
                "content": "好的，我已经了解你的命盘信息了。你想问什么？我会基于你的盘来回答。",
            })
        # 历史
        msgs.extend(self.history)
        # 当前问题
        msgs.append({"role": "user", "content": user_input})
        return msgs

    # ---- 同步对话 ----
    def chat(self, user_input: str) -> str:
        """单次对话，返回完整回答"""
        client = self._get_client()
        messages = self._build_messages(user_input)
        try:
            resp = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=False,
            )
            answer = resp.choices[0].message.content
        except OpenAIError as e:
            return f"❌ 大模型调用失败：{e}"

        # 写入历史
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": answer})
        return answer

    # ---- 流式对话 ----
    def chat_stream(self, user_input: str) -> Iterator[str]:
        """流式对话，逐字 yield"""
        client = self._get_client()
        messages = self._build_messages(user_input)
        try:
            stream = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
            )
            buf = []
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    buf.append(delta.content)
                    yield delta.content
            answer = "".join(buf)
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": answer})
        except OpenAIError as e:
            yield f"❌ 大模型调用失败：{e}"


# ---- 便捷函数 ----
def quick_ask(question: str, context_kwargs: Optional[dict] = None,
              mode: str = "auto") -> str:
    """一次性问答（不保留历史）"""
    chat = FortuneChat(mode=mode)
    if context_kwargs:
        chat.set_context(**context_kwargs)
    return chat.chat(question)
