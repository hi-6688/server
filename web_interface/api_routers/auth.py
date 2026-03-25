from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["auth"])

LOGIN_PASSWORD = "hmpb"
API_KEY = "AdminKey123456"

class LoginRequest(BaseModel):
    password: str

@router.post("/login")
def login(req: LoginRequest):
    """登入驗證，回傳 API Key"""
    if req.password == LOGIN_PASSWORD:
        return {"status": "ok", "key": API_KEY}
    else:
        raise HTTPException(status_code=401, detail="Invalid password")
