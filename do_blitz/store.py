from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import DateTime, Integer, String, Text, create_engine, delete, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from do_blitz.config import Settings, sqlalchemy_url


class CodeAlreadyExists(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Link:
    code: str
    long_url: str
    created_at: datetime
    hits: int


class LinkStore(Protocol):
    def ping(self) -> bool: ...
    def insert(self, link: Link) -> None: ...
    def get(self, code: str) -> Link | None: ...
    def increment_hits(self, code: str) -> Link | None: ...


class MemoryLinkStore:
    def __init__(self) -> None:
        self._rows: dict[str, Link] = {}

    def ping(self) -> bool:
        return True

    def insert(self, link: Link) -> None:
        if link.code in self._rows:
            raise CodeAlreadyExists(link.code)
        self._rows[link.code] = link

    def get(self, code: str) -> Link | None:
        return self._rows.get(code)

    def increment_hits(self, code: str) -> Link | None:
        current = self._rows.get(code)
        if current is None:
            return None
        updated = Link(
            code=current.code,
            long_url=current.long_url,
            created_at=current.created_at,
            hits=current.hits + 1,
        )
        self._rows[code] = updated
        return updated


class Base(DeclarativeBase):
    pass


class LinkRow(Base):
    __tablename__ = "links"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    long_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hits: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


def _from_row(row: LinkRow) -> Link:
    return Link(
        code=row.code,
        long_url=row.long_url,
        created_at=row.created_at,
        hits=row.hits,
    )


class PostgresLinkStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(sqlalchemy_url(database_url), pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self._session = sessionmaker(self.engine, expire_on_commit=False)

    def ping(self) -> bool:
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True

    def insert(self, link: Link) -> None:
        row = LinkRow(
            code=link.code,
            long_url=link.long_url,
            created_at=link.created_at,
            hits=link.hits,
        )
        with self._session() as session:
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise CodeAlreadyExists(link.code) from exc

    def get(self, code: str) -> Link | None:
        with self._session() as session:
            row = session.get(LinkRow, code)
            return _from_row(row) if row is not None else None

    def increment_hits(self, code: str) -> Link | None:
        stmt = (
            update(LinkRow)
            .where(LinkRow.code == code)
            .values(hits=LinkRow.hits + 1)
            .returning(LinkRow)
        )
        with self._session() as session:
            row = session.execute(stmt).scalar_one_or_none()
            session.commit()
            return _from_row(row) if row is not None else None

    def wipe(self) -> None:
        with self._session() as session:
            session.execute(delete(LinkRow))
            session.commit()


def build_store(settings: Settings) -> LinkStore:
    if settings.database_url:
        return PostgresLinkStore(settings.database_url)
    return MemoryLinkStore()
