from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import sys
import base64
import io

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import proxy_helpers
from dependencies import get_instance_or_404, verify_key

router = APIRouter(tags=["worlds"])

def get_instance(key: str, instance_id: str = "main"):
    verify_key(key)
    return get_instance_or_404(instance_id)

class WorldRequest(BaseModel):
    world: str

class UpdateRequest(BaseModel):
    url: str

@router.get("/worlds")
def list_worlds(instance = Depends(get_instance)):
    """列出所有世界"""
    if not proxy_helpers.is_vm2_running():
        return {"worlds": [], "active": "Offline"}

    res = proxy_helpers.proxy_to_agent("list_worlds", path=instance.path)
    if res.get('status') == 'success':
        return {"worlds": res.get("worlds", []), "active": res.get("active", "")}
    else:
        raise HTTPException(status_code=500, detail=res.get("message"))

@router.post("/switch_world")
def switch_world(req: WorldRequest, instance = Depends(get_instance)):
    """切換使用的世界"""
    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline")
    if not req.world:
        raise HTTPException(status_code=400, detail="No world name provided")
    
    try:
        props_path = os.path.join(instance.path, 'server.properties')
        res = proxy_helpers.proxy_to_agent("read_file", filepath=props_path)

        if res.get('status') == 'success':
            content = res.get('content', '')
            new_content = ''
            found = False
            for line in content.splitlines():
                if line.strip().startswith('level-name='):
                    new_content += f"level-name={req.world}\n"
                    found = True
                else:
                    new_content += line + '\n'
            if not found:
                new_content += f"level-name={req.world}\n"

            proxy_helpers.proxy_to_agent("write_file", filepath=props_path, content=new_content)

        return {"status": "switched"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete_world")
def delete_world(req: WorldRequest, instance = Depends(get_instance)):
    """刪除世界"""
    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline")

    if req.world:
        proxy_helpers.proxy_to_agent("delete_dir", path=os.path.join(instance.path, 'worlds', req.world))
        return {"status": "deleted"}
    raise HTTPException(status_code=400, detail="No world name provided")

@router.post("/reset_world")
def reset_world(instance = Depends(get_instance)):
    """重置世界地形 (保留設定與模組)"""
    try:
        if not proxy_helpers.is_vm2_running():
            raise HTTPException(status_code=409, detail="VM2 is offline")

        # 讀取使用中的世界名稱
        active_world = ''
        props_path = os.path.join(instance.path, 'server.properties')
        res_props = proxy_helpers.proxy_to_agent("read_file", filepath=props_path)
        if res_props.get('status') == 'success':
            content = res_props.get('content', '')
            for line in content.splitlines():
                if line.strip().startswith('level-name='):
                    active_world = line.strip().split('=', 1)[1]
                    break

        if not active_world:
            raise HTTPException(status_code=400, detail="Cannot determine active world")

        res = proxy_helpers.proxy_to_agent("reset_world",
            path=os.path.join(instance.path, 'worlds', active_world),
            screen_name=instance.screen_name)

        if res.get('status') == 'success':
            return {
                "status": "ok",
                "world": active_world,
                "message": "地形資料已重置，設定與模組已保留"
            }
        else:
            raise HTTPException(status_code=500, detail=res.get("message"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_world(
    key: str = Form(...),
    instance_id: str = Form("main"),
    file: UploadFile = File(...)
):
    """上傳世界地圖 (.mcworld / .zip)"""
    instance = get_instance(key, instance_id)
    
    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline")
    try:
        file_data = await file.read()
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        res = proxy_helpers.proxy_to_agent("upload_zip",
            path=os.path.join(instance.path, 'worlds'), file_data_base64=encoded_data)

        if res.get('status') == 'success':
            return {"status": "ok", "message": "Uploaded"}
        else:
            raise HTTPException(status_code=500, detail=res.get("message"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
def download_world(world: str, instance = Depends(get_instance)):
    """下載世界地圖為 zip"""
    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline")
    if not world:
        raise HTTPException(status_code=400, detail="No world specified")

    try:
        res = proxy_helpers.proxy_to_agent("download_world", path=os.path.join(instance.path, 'worlds', world))
        if res.get('status') == 'success' and 'base64_data' in res:
            data = base64.b64decode(res['base64_data'])
            return StreamingResponse(
                io.BytesIO(data), 
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{world}.zip"'}
            )
        else:
            raise HTTPException(status_code=404, detail="World folder not found or zip failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
def update_server(req: UpdateRequest, instance = Depends(get_instance)):
    """更新伺服器版本"""
    if not req.url:
        raise HTTPException(status_code=400, detail="No URL provided")
    if not proxy_helpers.is_vm2_running():
        raise HTTPException(status_code=409, detail="VM2 is offline")

    try:
        res = proxy_helpers.proxy_to_agent("update_server",
            path=instance.path, url=req.url, screen_name=instance.screen_name)
        if res.get('status') == 'success':
            return {"status": "updated"}
        else:
            raise HTTPException(status_code=500, detail=res.get("message"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
