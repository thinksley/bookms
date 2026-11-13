# 图书管理系统（FastAPI + Vue3）

## 界面预览

**图书管理** —— 封面、搜索、批量操作、回收站：

![图书管理](截图1.png)

**数据看板** —— 统计卡片、分类分布、借阅排行、借阅热力图：

![数据看板](截图2.png)

## 后端
cd backend
python -m venv venv
venv\Scripts\activate        (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

接口文档: http://127.0.0.1:8000/docs
默认管理员: admin / admin123（可在 backend/.env 中修改）

## 前端
cd frontend
npm install
npm run dev

访问: http://localhost:5173

## 数据库
请先在 MySQL 中创建数据库:
CREATE DATABASE IF NOT EXISTS myBigBig DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
表结构在后端启动时自动创建。
