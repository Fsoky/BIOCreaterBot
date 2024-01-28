from sqlalchemy import Integer, BigInteger, JSON, Text, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    bio: Mapped[str] = mapped_column(Text, nullable=True)
    entities: Mapped[list[dict]] = mapped_column(JSON, nullable=True)
    buttons: Mapped[list[dict]] = mapped_column(JSON, nullable=True)