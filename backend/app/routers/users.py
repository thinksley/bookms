from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserOut, UserPage, UserUpdate
from app.security import get_current_user, hash_password

# 用户管理仅管理员可操作
router = APIRouter(
    prefix="/api/users",
    tags=["用户管理"],
    dependencies=[Depends(get_current_user)],
)


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


def ensure_username_free(db: Session, username: str, exclude_id: Optional[int] = None) -> None:
    query = db.query(User).filter(User.username == username)
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail="该用户名已存在")


def is_last_admin(db: Session, user: User) -> bool:
    """该用户是管理员，且是系统中最后一个管理员。"""
    if not user.is_admin:
        return False
    admin_count = db.query(User).filter(User.is_admin.is_(True)).count()
    return admin_count <= 1


@router.get("", response_model=UserPage)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if keyword:
        query = query.filter(User.username.like(f"%{keyword}%"))
    total = query.count()
    items = query.order_by(User.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "items": items}


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ensure_username_free(db, data.username)
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        is_admin=data.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)
    updates = data.model_dump(exclude_unset=True)

    new_username = updates.get("username")
    if new_username:
        ensure_username_free(db, new_username, exclude_id=user_id)

    # 不允许把最后一个管理员降级为普通用户
    if updates.get("is_admin") is False and is_last_admin(db, user):
        raise HTTPException(status_code=400, detail="系统至少需要保留一个管理员")

    for field, value in updates.items():
        if field == "password":
            user.hashed_password = hash_password(value)
        else:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的账号")
    if is_last_admin(db, user):
        raise HTTPException(status_code=400, detail="不能删除最后一个管理员")
    db.delete(user)
    db.commit()
    return None
