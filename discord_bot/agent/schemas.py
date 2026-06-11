# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any

class MemoryState(BaseModel):
    """
    大腦內部評估對話與心跳休眠狀態的驗證模型。
    """
    needs_reply: bool = Field(description="判斷目前對話歷史是否需要我回答。若需要填 True，不需要或決定休眠填 False。")
    current_goal: str = Field(description="我目前的工作目標或要處理的實體。")
    suggested_sleep_seconds: int = Field(description="我決定接下來要主動休眠多久（秒）？這是妳用來保護「生命配額」的唯一手段。若配額充足且群組熱鬧，填 3600；若配額快耗盡，請大膽填寫 14400 或更長，直到下午三點重置。")
    sleep_intent: Optional[str] = Field(default=None, description="如果妳設定了休眠秒數，請在這裡寫下妳『醒來後要做什麼』(例如：『等待60秒後回答問題』)。如果只是普通的長眠，請填 null。")

class PersonaResponse(BaseModel):
    """
    主大腦擬人化生成回覆的驗證模型。
    """
    situation_analysis: str = Field(description="簡短分析目前群組的氣氛與上下文脈絡。")
    internal_thought: str = Field(description="妳在心裡的 OS。決定用什麼態度回覆。")
    final_speech: Optional[str] = Field(default=None, description="最後要在 Discord 說出口的話。如果覺得不想回，請填 null。")

class SleepScheduleParams(BaseModel):
    """
    大腦定時休眠與甦醒排程的參數 Schema。
    """
    seconds: int = Field(
        description="我決定接下來要主動休眠多久（秒）？這是妳用來保護「生命配額」的唯一手段。若配額充足且群組熱鬧，建議設定 3600；若配額快耗盡，請設定 14400 或更長。"
    )
    intent: Optional[str] = Field(
        default=None,
        description="醒來後要主動做的事情備忘錄。如果是一般長眠，填 null。"
    )

    @field_validator("seconds")
    @classmethod
    def enforce_boundaries(cls, v: int) -> int:
        """限制最小與最大休眠時間 (enforce bounds for safety)"""
        if v < 10:
            return 10
        if v > 86400:  # 限制最大為 24 小時
            return 86400
        return v

    @field_validator("intent")
    @classmethod
    def normalize_intent(cls, v: Optional[str]) -> Optional[str]:
        """自動清理 'null' 字串 (clean null strings from LLM)"""
        if v and v.strip().lower() in ("null", "none", ""):
            return None
        return v
