"""ai 包：大模型对话层"""
from .chat import FortuneChat, ChatConfig, quick_ask
from .prompts import (
    SYSTEM_PROMPT_BASE,
    get_system_prompt,
    build_user_context,
    DISCLAIMER_FOOTER,
)

__all__ = [
    "FortuneChat", "ChatConfig", "quick_ask",
    "SYSTEM_PROMPT_BASE", "get_system_prompt",
    "build_user_context", "DISCLAIMER_FOOTER",
]
