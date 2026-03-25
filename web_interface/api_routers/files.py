from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import proxy_helpers
from dependencies import get_instance_or_404, verify_key

router = APIRouter(tags=["files"])

def get_instance(key: str, instance_id: str = "main"):
    verify_key(key)
    return get_instance_or_404(instance_id)

class WriteRequest(BaseModel):
    file: str
    content: str

@router.get("/read")
def read_file(file: str, lines: str = "", instance = Depends(get_instance)):
    """讀取設定檔 (server.properties, allowlist.json 等)"""
    allowed_files = ['server.properties', 'whitelist.json', 'permissions.json', 'allowlist.json', 'bedrock_screen.log']
    if file not in allowed_files:
        raise HTTPException(status_code=404, detail="File not allowed or not found")

    fpath = os.path.join(instance.path, file)

    # 優先檢查離線快取
    cached_content = proxy_helpers.read_offline_cache(instance.path, file)
    if cached_content is not None:
        return {"content": cached_content, "source": "offline_cache"}

    if proxy_helpers.is_vm2_running():
        if lines and lines.isdigit():
            res = proxy_helpers.proxy_to_agent("read_log_tail", filepath=fpath, lines=int(lines))
        else:
            res = proxy_helpers.proxy_to_agent("read_file", filepath=fpath)

        if res.get('status') == 'success':
            return {"content": res.get('content', '')}
        else:
            raise HTTPException(status_code=404, detail="File content not found")
    else:
        raise HTTPException(status_code=404, detail="VM2 is offline and no cache available")

@router.post("/write")
def write_file(req: WriteRequest, instance = Depends(get_instance)):
    """覆寫設定檔"""
    allowed_files = ['server.properties', 'whitelist.json', 'permissions.json', 'allowlist.json']
    if req.file not in allowed_files:
        raise HTTPException(status_code=403, detail="File not allowed")

    full_dest = os.path.join(instance.path, req.file)

    try:
        if proxy_helpers.is_vm2_running():
            res = proxy_helpers.proxy_to_agent("write_file", filepath=full_dest, content=req.content)
            if res.get('status') == 'success':
                return {"status": "saved"}
            else:
                raise HTTPException(status_code=500, detail=res.get('message'))
        else:
            # 離線快取
            proxy_helpers.save_offline_cache(instance.path, req.file, req.content)
            return {"status": "saved_offline"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
