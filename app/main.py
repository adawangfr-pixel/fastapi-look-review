"""FastAPI 应用入口。

负责创建应用、启动时建表、注册路由，并挂载静态页面与上传目录。
保留 FastAPI 自动生成的 /docs 文档。
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import create_db_and_tables
from app.routers import export, products, review, upload

# 静态页面目录与上传目录
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOAD_DIR = "uploads"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表并确保上传目录存在。"""
    create_db_and_tables()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(title="商品 look 审核与导出系统", lifespan=lifespan)

# 注册四个路由模块
app.include_router(upload.router)
app.include_router(products.router)
app.include_router(review.router)
app.include_router(export.router)

# 挂载静态页面（原生 HTML）
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# 挂载上传目录，便于前端通过 /uploads/... 显示图片
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def index():
    """根路径重定向到上传页面。"""
    return RedirectResponse(url="/static/upload.html")
