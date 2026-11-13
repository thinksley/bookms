from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Book, Category, User
from app.security import hash_password

# 已存在的表 create_all 不会自动加列，这里登记缺失字段的 DDL，启动时补齐
COLUMNS_TO_ADD = {
    "books": {
        "deleted_at": "DATETIME",
    },
    "borrow_records": {
        "reader_id": "INTEGER",
        "renewed_count": "INTEGER DEFAULT 0",
    },
}


def ensure_book_columns(engine: Engine) -> None:
    """轻量迁移：为已存在的表补齐新增字段（幂等，可重复执行）。"""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table, columns in COLUMNS_TO_ADD.items():
        if table not in existing_tables:
            continue  # 新库由 create_all 直接建全表
        existing = {c["name"] for c in inspector.get_columns(table)}
        missing = {k: v for k, v in columns.items() if k not in existing}
        if not missing:
            continue
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        print(f"{table} 表已补齐 {len(missing)} 个新字段: {', '.join(missing)}")


def seed_categories(db: Session) -> None:
    """把已有图书的分类补进字典表（幂等）。"""
    existing = {c.name for c in db.query(Category).all()}
    book_categories = {row[0] for row in db.query(Book.category).all() if row[0]}
    new = book_categories - existing
    for name in new:
        db.add(Category(name=name))
    if new:
        db.commit()
        print(f"分类字典已补充: {', '.join(sorted(new))}")


def create_first_admin(db: Session) -> None:
    """启动时若不存在管理员账号，则自动创建一个。"""
    exists = db.query(User).filter(User.username == settings.FIRST_ADMIN_USERNAME).first()
    if exists:
        return
    admin = User(
        username=settings.FIRST_ADMIN_USERNAME,
        hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
        is_admin=True,
    )
    db.add(admin)
    db.commit()
    print(f"已创建默认管理员：{settings.FIRST_ADMIN_USERNAME}")
