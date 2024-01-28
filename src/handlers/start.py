from aiogram import Router
from aiogram.types import Message, KeyboardButton, KeyboardButtonRequestChat, ChatAdministratorRights
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User

router = Router()


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession) -> None:
    user = await session.scalar(select(User).where(User.user_id == message.from_user.id))
    pattern = {}

    if not user:
        session.add(User(user_id=message.from_user.id))
        await session.commit()

        pattern["text"] = (
            "<b>👋 Привет, давай я помогу тебе создать BIO!</b>\n"
            "Чтобы начать введи команду /bio"
        )
        pattern["reply_markup"] = (
            ReplyKeyboardBuilder()
            .button(text="✍ Изменить текст")
            .button(text="🔲 Добавить кнопку")
            .add(
                KeyboardButton(
                    text="➕ Пригласить бота",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=message.from_user.id,
                        chat_is_channel=True
                    )
                )
            )
        ).adjust(2).as_markup(resize_keyboard=True)
    else:
        if user.buttons:
            inline_markup = InlineKeyboardBuilder()
            [inline_markup.button(**button) for button in user.buttons]
            inline_markup = inline_markup.adjust(2).as_markup()
        else:
            inline_markup = None

        pattern["text"] = user.bio if user.bio else "<b>👀 Тут будет твой текст...</b>"
        pattern["reply_markup"] = inline_markup
        pattern["entities"] = user.entities
        pattern["parse_mode"] = None

    await message.answer(**pattern)