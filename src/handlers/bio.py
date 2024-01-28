from typing import Any

from aiogram import Router, F, html
from aiogram.types import Message
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from states import BIOTextForm, BIOButtonForm
from db import User

router = Router()


@router.message(or_f(Command("bio"), F.text == "✍ Изменить текст"))
async def change_the_text(message: Message, state: FSMContext) -> None:
    await message.answer("<b>✍ Вперед писать новый текст!</b>")
    await state.set_state(BIOTextForm.text)


@router.message(BIOTextForm.text, F.text)
async def change_the_text_form(message: Message, state: FSMContext, session: AsyncSession) -> Any:
    safe_text = html.quote(message.text)
    if len(safe_text) > 4096:
        return await message.answer("<b>😱 Слишком большой текст!</b>")

    buttons = await session.scalar(select(User.buttons).where(User.user_id == message.from_user.id))
    if buttons:
        inline_markup = InlineKeyboardBuilder()
        [inline_markup.button(**button) for button in buttons]
        inline_markup = inline_markup.adjust(2).as_markup()
    else:
        inline_markup = None

    await session.execute(update(User).values(bio=safe_text, entities=message.model_dump()["entities"]))
    await session.commit()

    await message.answer(
        text=message.text,
        entities=message.entities,
        parse_mode=None,
        reply_markup=inline_markup
    )
    await state.clear()


@router.message(or_f(Command("add_button"), F.text == "🔲 Добавить кнопку"))
async def add_button(message: Message, state: FSMContext) -> None:
    await message.answer("<b>✍ Введи текст для своей кнопки</b>")
    await state.set_state(BIOButtonForm.text)


@router.message(BIOButtonForm.text, F.text)
async def add_button_text(message: Message, state: FSMContext) -> Any:
    safe_text = html.quote(message.text)
    if len(safe_text) > 32:
        return await message.answer("😱 Слишком большой текст!")

    await message.answer("<b>🔗 Введи ссылку для своей кнопки</b>")
    await state.update_data(text=safe_text)
    await state.set_state(BIOButtonForm.url)


@router.message(BIOButtonForm.url, F.text)
async def add_button_url(message: Message, state: FSMContext, session: AsyncSession) -> Any:
    if message.entities:
        for item in message.entities:
            if item.type == "url":
                data = await state.get_data()
                await state.clear()

                buttons = await session.scalar(select(User.buttons).where(User.user_id == message.from_user.id))
                if not buttons: buttons = []
                buttons.append({"text": data["text"], "url": item.extract_from(message.text)})

                await session.execute(
                    update(User)
                    .values(buttons=buttons)
                )
                await session.commit()

                return await message.answer("<b>🔲 Кнопка была добавлена!</b>")
    await message.answer("<b>🔗 Ссылка не обнаружена!</b>")