from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger
from app.core.database import Base

class BaseModel(Base):
    """
    所有业务 Model 的基类
    """
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )