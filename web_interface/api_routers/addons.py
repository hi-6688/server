from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import os
import sys
import base64

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import proxy_helpers
from dependencies import get_instance_or_404, verify_key

router = APIRouter(tags=["addons"])

def get_instance(key: str, instance_id: str = "main"):
    verify_key(key)
    return get_instance_or_404(instance_id)

class DeleteAddonRequest(BaseModel):
    name: str
    type: str = "behavior_packs"

@router.get("/addons")
def list_addons(instance = Depends(get_instance)):
    """列出所有已安裝模組"""
    if not proxy_helpers.is_vm2_running():
        return {"addons": []}

    res = proxy_helpers.proxy_to_agent("list_addons", path=instance.path)
    if res.get('status') == 'success':
        return {"addons": res.get("addons", [])}
    else:
        raise HTTPException(status_code=500, detail=res.get("message"))

@router.post("/addon/upload")
async def upload_addon(
    key: str = Form(...),
    instance_id: str = Form("main"),
    type: str = Form(""),
    file: UploadFile = File(...)
):
    """上傳模組檔案"""
    instance = get_instance(key, instance_id)

    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline")
    try:
        file_data = await file.read()
        original_filename = file.filename or "addon.zip"
        
        encoded_data = base64.b64encode(file_data).decode('utf-8')

        res = proxy_helpers.proxy_to_agent("upload_addon",
            path=instance.path, addon_type=type,
            original_filename=original_filename, file_data_base64=encoded_data)

        if res.get('status') == 'success':
            return {
                "status": "ok",
                "message": res.get("message", "Uploaded"),
                "packs": res.get("packs", [])
            }
        else:
            raise HTTPException(status_code=500, detail=res.get("message"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/addon/delete")
def delete_addon(req: DeleteAddonRequest, instance = Depends(get_instance)):
    """刪除模組"""
    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline")

    if not req.name:
        raise HTTPException(status_code=400, detail="No addon name")

    try:
        proxy_helpers.proxy_to_agent("delete_dir", path=os.path.join(instance.path, req.type, req.name))
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
