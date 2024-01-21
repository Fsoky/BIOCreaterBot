import asyncio
from typing import Any
from contextlib import suppress

from aiogram import Router, Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.scene import Scene, SceneRegistry, ScenesManager, on
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticDatabase as MDB
from pymongo.errors import DuplicateKeyError


def inline_builder(
    text: str | list[str],
    callback_data: str | list[str],
    sizes: int | list[int]=2,
    **kwargs
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()

    text = [text] if isinstance(text, str) else text
    callback_data = [callback_data] if isinstance(callback_data, str) else callback_data
    sizes = [sizes] if isinstance(sizes, int) else sizes

    [
        builder.button(text=txt, callback_data=cb)
        for txt, cb in zip(text, callback_data)
    ]

    builder.adjust(*sizes)
    return builder.as_markup(**kwargs)


def bio_kb() -> InlineKeyboardBuilder:
    text = [
        "☕ Заголовок", "🍕 Короткое описание",
        "🍋 Большое описание", "🍍 Добавить кнопку",
        "🍬 Завершить"
    ]
    callback_data = [
        BIOFactory(action="headline").pack(),
        BIOFactory(action="short-description").pack(),
        BIOFactory(action="large-description").pack(),
        BIOFactory(action="add-button").pack(),
        BIOFactory(action="exit").pack()
    ]

    return inline_builder(text, callback_data)


class BIOFactory(CallbackData, prefix="bio"):
    action: str
    value: Any = None


class BIOScene(Scene, state="create_bio"):

    @on.message.enter()
    @on.callback_query(BIOFactory.filter(F.action))
    async def on_enter(
        self, message: Message | CallbackQuery, state: FSMContext,
        db: MDB, callback_data: BIOFactory | None=None
    ) -> Any:
        bio = await db.bio.find_one({"_id": message.from_user.id})

        all_entities = [
            *bio.get("headline").get("entities"),
            *bio.get("short-description").get("entities"),
            *bio.get("large-description").get("entities")
        ]
        pattern = {
            "text": (
                f"{bio.get('headline').get('text')}\n" 
                f"{bio.get('short-description').get('text')}\n\n"
                f"{bio.get('large-description').get('text')}"
            ),
            "reply_markup": bio_kb(),
            "entities": all_entities,
            "parse_mode": None
        }

        if isinstance(message, CallbackQuery):
            if callback_data.action == "headline":
                pattern["text"] = "<b>Введи новое название заголовка...</b>"
            elif callback_data.action == "short-description":
                pattern["text"] = "<b>Введи новое короткое описание...</b>"
            elif callback_data.action == "large-description":
                pattern["text"] = "<b>Введи новое основное описание...</b>"
            
            if callback_data.action != "cancel":
                pattern["reply_markup"] = inline_builder("🍷 Отмена", BIOFactory(action="cancel").pack())
                pattern["parse_mode"] = ParseMode.HTML
            
            await state.update_data(msg_id=message.message.message_id, action=callback_data.action)
            return await message.message.edit_text(**pattern)
        await message.answer(**pattern)
    
    @on.message.exit()
    async def on_exit(self, message: Message, state: FSMContext) -> Any:
        data = await state.get_data()
        print(data)

    @on.message(F.text)
    async def parse_text(self, message: Message, state: FSMContext, bot: Bot, db: MDB) -> Any:
        bio = await db.bio.find_one({"_id": message.from_user.id})
        data = await state.get_data()

        entities = message.model_dump().get("entities")
        if entities:
            if data.get("action") != "headline" and data.get("action") != "large-description":
                entities[0]["offset"] = entities[0]["offset"] + len(bio.get("headline").get("text")) + 1
            elif data.get("action") != "headline" and data.get("action") != "short-description":
                entities[0]["offset"] = \
                    entities[0]["offset"] \
                    + len(bio.get("headline").get("text")) \
                    + len(bio.get("short-description").get("text")) + 3
        else:
            entities = []
        
        update = {"$set": {
            f"{data.get('action')}.text": message.text,
            f"{data.get('action')}.entities": entities
        }}

        await db.bio.update_one({"_id": message.from_user.id}, update)
        await bot.edit_message_text(
            text=message.text,
            chat_id=message.chat.id,
            message_id=data.get("msg_id"),
            reply_markup=bio_kb(),
            entities=message.entities,
            parse_mode=None
        )
        await message.delete()


router = Router()
router.message.filter(F.from_user.id == 1490170564)
router.message.register(BIOScene.as_handler(), Command("bio"))


@router.message(CommandStart())
async def start(message: Message, scenes: ScenesManager, db: MDB) -> None:
    with suppress(DuplicateKeyError):
        await db.bio.insert_one({
            "_id": message.from_user.id,
            "headline": {"text": "Заголовок", "entities": []},
            "short-description": {"text": "Короткое описание", "entities": []},
            "large-description": {"text": "Полное описание", "entities": []},
        })

    await scenes.close()
    await message.reply("Введи команду /bio")


async def main() -> None:
    bot = Bot(open("TOKEN.txt").read(), parse_mode=ParseMode.HTML)
    dp = Dispatcher(events_isolation=SimpleEventIsolation())

    cluster = AsyncIOMotorClient(host="localhost", port=27017)
    db = cluster.biodb

    dp.include_router(router)

    scene_registry = SceneRegistry(dp)
    scene_registry.add(BIOScene)

    await bot.delete_webhook(True)
    await dp.start_polling(bot, db=db)


if __name__ == "__main__":
    asyncio.run(main())