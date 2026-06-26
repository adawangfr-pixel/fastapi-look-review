"""数据库引擎与会话管理。

使用 SQLModel/SQLAlchemy 创建一个本地 SQLite 引擎（文件 database.db），
并提供建表函数与 FastAPI 依赖用的会话生成器。
"""

from sqlmodel import SQLModel, Session, create_engine

# SQLite 数据库文件名
SQLITE_FILE_NAME = "database.db"
SQLITE_URL = f"sqlite:///{SQLITE_FILE_NAME}"

# check_same_thread=False 允许在 FastAPI 的多线程环境中使用同一个连接；
# echo=False 关闭 SQL 日志输出。
engine = create_engine(
    SQLITE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables() -> None:
    """根据所有 SQLModel 表模型在数据库中创建表（已存在则跳过）。"""
    # 导入 models 以确保所有表模型都已注册到 SQLModel.metadata
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 依赖：为每个请求提供一个数据库会话，请求结束后自动关闭。"""
    with Session(engine) as session:
        yield session
