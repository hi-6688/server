from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from dependencies import instance_manager, verify_key

router = APIRouter(tags=["instances"], prefix="/instances")

# 全局金鑰驗證
def require_key(key: str):
    verify_key(key)

class CreateInstanceReq(BaseModel):
    name: str
    port: str
    discord_channel_id: str = ""

class DeleteInstanceReq(BaseModel):
    instance_id: str

class UpdateInstanceReq(BaseModel):
    uuid: str
    name: str
    port: str
    discord_channel_id: str = ""

@router.get("/list", dependencies=[Depends(require_key)])
def list_instances():
    """列出所有伺服器實例"""
    insts = []
    for i in instance_manager.get_all_instances():
        d = i.to_dict()
        d['is_running'] = i.is_running()
        insts.append(d)
    return {"instances": insts}

@router.post("/create", dependencies=[Depends(require_key)])
def create_instance(req: CreateInstanceReq):
    """建立新伺服器實例"""
    try:
        new_inst = instance_manager.create_instance(req.name, req.port, req.discord_channel_id)
        return {"status": "ok", "instance": new_inst.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete", dependencies=[Depends(require_key)])
def delete_instance(req: DeleteInstanceReq):
    """刪除伺服器實例"""
    try:
        instance_manager.delete_instance(req.instance_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update", dependencies=[Depends(require_key)])
def update_instance(req: UpdateInstanceReq):
    """更新實例設定"""
    try:
        updated = instance_manager.update_instance(req.uuid, req.name, req.port, req.discord_channel_id)
        return {"status": "ok", "instance": updated.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
