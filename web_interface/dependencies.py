from fastapi import HTTPException
from pydantic import BaseModel
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import InstanceManager

API_KEY = "AdminKey123456"

# 全局實例管理器
instance_manager = InstanceManager()

def verify_key(key: str):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

class BaseRequestWithKey(BaseModel):
    key: str
    instance_id: str = "main"

def get_instance_or_404(instance_id: str):
    instance = instance_manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance
