from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SystemSetting, User
from app.schemas import SettingsOut, SettingsUpdate
from app.security import get_current_user

router = APIRouter(prefix="/api/settings", tags=["系统设置"])

# 全局借阅规则的默认值：settings 表里缺哪项就用哪个兜底
DEFAULT_RULES = {
    "borrow_days": 31,  # 默认借期（天）
    "renew_days": 30,  # 续借顺延天数
    "fine_per_day": 0.5,  # 逾期日罚金（元），为罚款功能预留
    "max_borrow": 5,  # 新读者默认可借上限
}

# 库里存的是字符串，读出来要按这个表转回数字
INT_KEYS = {"borrow_days", "renew_days", "max_borrow"}
FLOAT_KEYS = {"fine_per_day"}


def get_rules(db: Session) -> dict:
    """读出全部规则并转成正确的类型，borrows / readers 都靠它取配置。"""
    rows = db.query(SystemSetting).all()
    raw = {row.key: row.value for row in rows}
    rules = {}
    for key, default in DEFAULT_RULES.items():
        value = raw.get(key, str(default))
        if key in INT_KEYS:
            rules[key] = int(float(value))
        elif key in FLOAT_KEYS:
            rules[key] = float(value)
        else:
            rules[key] = value
    return rules


def seed_settings(db: Session) -> None:
    """启动时补齐缺失的设置项（幂等：库里已有的不动）。"""
    for key, default in DEFAULT_RULES.items():
        exists = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not exists:
            db.add(SystemSetting(key=key, value=str(default)))
    db.commit()


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_rules(db)


@router.put("", response_model=SettingsOut)
def update_settings(
    data: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可修改系统设置")
    for key, value in data.model_dump(exclude_unset=True).items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row:
            row.value = str(value)
        else:
            db.add(SystemSetting(key=key, value=str(value)))
    db.commit()
    return get_rules(db)
