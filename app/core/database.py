from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.settings import settings
from sqlalchemy.orm import DeclarativeBase

aengine = create_async_engine(settings.DATABASE_URL, echo=True)
async_session_local = async_sessionmaker(bind= aengine, expire_on_commit= False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_local() as session:
        yield session

async def init_db():
    async with aengine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
