from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    subject_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_name: Mapped[str] = mapped_column(String, nullable=False)
    subject_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True
    )
    universities: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True
    )
    slugs: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True
    )
    semester: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )