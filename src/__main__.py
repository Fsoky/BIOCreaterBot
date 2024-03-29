import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, AsyncEngine, create_async_engine

from handlers import setup_message_routers
from middlewares import DBSessionMiddleware
from db import Base

from config import BOT_TOKEN, DATABASE_URL


async def on_startup(_engine: AsyncEngine) -> None:
    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def on_shutdown(bot: Bot, session: AsyncSession) -> None:
    await bot.session.close()
    await session.close()


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(_engine=engine)

    dp.update.middleware(DBSessionMiddleware(sessionmaker))

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    message_routers = setup_message_routers()
    dp.include_router(message_routers)

    await bot.delete_webhook(True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())