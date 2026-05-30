from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite 数据库连接 URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# 创建数据库引擎
# connect_args={"check_same_thread": False} 仅适用于 SQLite，确保线程安全
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建数据库会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建模型基类
Base = declarative_base()


def get_db():
    """
    获取数据库会话的依赖函数
    使用 FastAPI 的依赖注入系统自动管理数据库连接
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()