from datetime import date

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class Category(Base):
    """分类字典：保证图书分类的数据一致性。"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Reader(Base):
    """读者档案：借阅挂在读者名下。"""

    __tablename__ = "readers"

    id = Column(Integer, primary_key=True, index=True)
    card_no = Column(String(20), unique=True, nullable=True)  # 读者证号
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    max_borrow = Column(Integer, nullable=False, default=5)  # 可借上限
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class BorrowRecord(Base):
    """借阅记录：书名/读者名做快照冗余，删除后历史仍可读。"""

    __tablename__ = "borrow_records"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="SET NULL"), nullable=True, index=True)
    book_title = Column(String(200), nullable=False)
    reader_id = Column(Integer, ForeignKey("readers.id", ondelete="SET NULL"), nullable=True, index=True)
    borrower_name = Column(String(50), nullable=False)
    borrow_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="在借", index=True)  # 在借 / 已还
    renewed_count = Column(Integer, nullable=False, default=0)  # 续借次数
    operator = Column(String(50), nullable=True)  # 经手管理员
    remark = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    @property
    def display_status(self) -> str:
        """逾期为动态判定：在借且已过应还日期。"""
        if self.status == "在借" and self.due_date is not None and self.due_date < date.today():
            return "逾期"
        return self.status


class SystemSetting(Base):
    """系统设置：键值对存储，一行一条规则，改了立即对全站生效。"""

    __tablename__ = "system_settings"

    key = Column(String(50), primary_key=True)  # 设置项名，如 borrow_days
    value = Column(String(100), nullable=False)  # 值统一存字符串，用时再转类型
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    # ---- 基本信息 ----
    title = Column(String(200), nullable=False, index=True)
    subtitle = Column(String(200), nullable=True)          # 副标题
    original_title = Column(String(200), nullable=True)    # 原作名（外文书原名）
    author = Column(String(100), nullable=False)
    translator = Column(String(100), nullable=True)        # 译者
    isbn = Column(String(20), unique=True, nullable=True)
    series = Column(String(100), nullable=True)            # 丛书系列
    language = Column(String(50), nullable=True)           # 语种
    # ---- 出版信息 ----
    publisher = Column(String(100), nullable=True)
    publish_place = Column(String(100), nullable=True)     # 出版地
    publish_date = Column(Date, nullable=True)             # 出版日期
    edition = Column(String(50), nullable=True)            # 版次，如 "第2版"
    binding = Column(String(20), nullable=True)            # 装帧：平装/精装
    book_format = Column(String(20), nullable=True)        # 开本，如 "16开"
    page_count = Column(Integer, nullable=True)            # 页数
    price = Column(Float, default=0)                       # 定价
    # ---- 分类与内容 ----
    category = Column(String(50), nullable=True, index=True)  # 分类
    tags = Column(String(200), nullable=True)              # 标签，逗号分隔
    summary = Column(Text, nullable=True)                  # 内容简介
    author_intro = Column(Text, nullable=True)             # 作者简介
    catalog = Column(Text, nullable=True)                  # 目录
    # ---- 馆藏信息 ----
    barcode = Column(String(50), nullable=True)            # 条形码
    call_number = Column(String(100), nullable=True)       # 索书号
    location = Column(String(100), nullable=True)          # 馆藏位置
    source = Column(String(50), nullable=True)             # 来源：购买/捐赠/调拨
    cover_url = Column(String(500), nullable=True)         # 封面图片链接
    stock = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True, index=True)  # 软删除时间，NULL=在库
    created_at = Column(DateTime, server_default=func.now())
