from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  确保模型已注册，create_all 才能建表
from app.database import Base, SessionLocal, engine
from app.init_db import create_first_admin, ensure_book_columns, seed_categories
from app.routers import auth, books, borrows, categories, readers, stats, uploads, users
from app.routers.settings import router as settings_router, seed_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_book_columns(engine)
    with SessionLocal() as db:
        create_first_admin(db)
        seed_categories(db)
        seed_settings(db)
    yield


app = FastAPI(title="图书管理系统 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(users.router)
app.include_router(borrows.router)
app.include_router(readers.router)
app.include_router(categories.router)
app.include_router(stats.router)
app.include_router(uploads.router)
app.include_router(settings_router)

# 封面等上传文件的静态访问（无需鉴权，路径含随机文件名）
app.mount("/api/uploads", StaticFiles(directory=uploads.UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"message": "图书管理系统 API 运行中，文档见 /docs"}
