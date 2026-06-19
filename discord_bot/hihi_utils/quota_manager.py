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
        檢查配額，如果未滿則遞增並儲存，返回 True；如果已滿則返回 False。
        """
        quota_date_str = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d')
        
        # 跨日重置
        if self.daily_usage.get("date") != quota_date_str:
            self.daily_usage = {"date": quota_date_str, "requests": 0, "tokens": 0}
            
        # 超限防禦
        if self.daily_usage["requests"] >= self.daily_limit:
            print(f"🚨 [Global Ledger] 物理超限！今日額度已用完 ({self.daily_usage['requests']}/{self.daily_limit})")
            return False
            
        if self.daily_usage["requests"] >= (self.daily_limit * 0.9):
            print(f"⚠️ [Global Ledger] 警告：今日額度已達 90% ({self.daily_usage['requests']}/{self.daily_limit})")
            
        self.daily_usage["requests"] += 1
        self._save_usage()
        print(f"📊 [Global Ledger] 今日累積呼叫: {self.daily_usage['requests']} 次 / {self.daily_limit} 次上限")
        return True
