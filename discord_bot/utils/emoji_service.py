# -*- coding: utf-8 -*-
import os
import json

class EmojiService:
    def __init__(self, emoji_file: str, meanings_file: str):
        self.emoji_file = emoji_file
        self.meanings_file = meanings_file
        self.emojis = self._load_json(emoji_file, {})
        self.emoji_meanings = self._load_json(meanings_file, {})

    def _load_json(self, path, default):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except:
                    return default
        return default

    def replace_emojis(self, text: str) -> str:
        """
        將文字中所有的 [表情代碼] 物理替換為實體 Discord Emoji ID。
        """
        if not text:
            return text
        final_text = text
        for k, v in self.emojis.items():
            final_text = final_text.replace(f"[{k}]", v)
        return final_text

    def get_emoji_prompt_docs(self) -> str:
        """
        生成注入 System Prompt 的表情包文檔。
        """
        emoji_list = []
        for k, code in self.emojis.items():
            desc = self.emoji_meanings.get(k, k) 
            if k.startswith("UI_") or "載入中" in desc:
                continue
            emoji_list.append(f"- [{k}]: {desc} (Code: `{code}`)")
        return "\n".join(emoji_list)
