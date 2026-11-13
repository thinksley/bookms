import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.security import get_current_user

router = APIRouter(
    prefix="/api/uploads",
    tags=["文件上传"],
    dependencies=[Depends(get_current_user)],
)

# 封面保存目录，静态文件由 main.py 挂载在 /api/uploads 下
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
COVER_DIR = UPLOAD_DIR / "covers"
COVER_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/cover")
async def upload_cover(file: UploadFile = File(...), _: None = Depends(get_current_user)):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail="仅支持 jpg / jpeg / png / webp 图片")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    name = f"{uuid.uuid4().hex}.{ext}"
    (COVER_DIR / name).write_bytes(content)
    return {"url": f"/api/uploads/covers/{name}"}
