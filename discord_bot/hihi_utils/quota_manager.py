# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

class QuotaManager:
    def __init__(self, usage_file: str, daily_limit: int = 500):
        self.usage_file = usage_file
        self.daily_limit = daily_limit
        self.daily_usage = self._load_usage()

    def _load_usage(self):
        if os.path.exists(self.usage_file):
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except:
                    pass
        return {"date": "", "requests": 0, "tokens": 0}

    def _save_usage(self):
        with open(self.usage_file, 'w', encoding='utf-8') as f:
            json.dump(self.daily_usage, f, ensure_ascii=False, indent=2)

    def check_and_increment(self) -> bool:
        """
        記錄並遞增發言次數，目前已取消額度限制，恆返回 True。
        """
        quota_date_str = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d')
        
        # 跨日重置
        if self.daily_usage.get("date") != quota_date_str:
            self.daily_usage = {"date": quota_date_str, "requests": 0, "tokens": 0}
            
        self.daily_usage["requests"] += 1
        self._save_usage()
        print(f"📊 [Global Ledger] 今日累積呼叫: {self.daily_usage['requests']} 次 (無額度限制)")
        return True
