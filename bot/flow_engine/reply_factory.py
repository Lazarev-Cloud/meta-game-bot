import logging
from copy import deepcopy

from aiogram.types import (
    Message, CallbackQuery, InputMediaPhoto, InputMediaVideo,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext

from app.translator import t

log = logging.getLogger(__name__)


class ReplyFactory:
    DEFAULT_PARSE_MODE = "HTML"

    @classmethod
    async def send(cls, event: Message | CallbackQuery, state: FSMContext, flow_config: dict, step_id: str) -> None:
        flow_config = await cls._prepare_config(flow_config, step_id)

        reply_type = flow_config.get("reply_type", "new")
        preserve_message = flow_config.get("preserve_message", False)
        media = flow_config.get("media")
        files = flow_config.get("files")
        poll = flow_config.get("poll")
        options = flow_config.get("options")

        data = await state.get_data()
        prompt_key = flow_config.get("prompt") or f"{step_id}.prompt"
        prompt = t(prompt_key, **data)

        keyboard = await cls._render_keyboard(options) if options else None
        chat_id = event.chat.id if isinstance(event, Message) else event.message.chat.id
        bot = event.bot

        if reply_type == "edit" and isinstance(event, CallbackQuery):
            if not preserve_message:
                await cls._delete_message(event)
                await cls._send_all(bot, chat_id, prompt, media, files, poll, keyboard)
            else:
                await cls._edit_message(event, prompt, keyboard)
        elif reply_type == "reply":
            await cls._reply_message(event, prompt, media, files, keyboard)
        else:  # new
            await cls._send_all(bot, chat_id, prompt, media, files, poll, keyboard)

    @staticmethod
    async def _delete_message(event: CallbackQuery):
        try:
            await event.message.delete()
        except Exception as e:
            log.warning(f"Failed to delete message: {e}")

    @staticmethod
    async def _send_all(bot, chat_id, prompt, media, files, poll, keyboard):
        if media:
            if len(media) == 1:
                # 📷 Одно медиа: сразу с текстом и клавиатурой
                item = media[0]
                if item["type"] == "photo":
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=item["media"],
                        caption=prompt or item.get("caption"),
                        reply_markup=keyboard,
                        parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
                    )
                elif item["type"] == "video":
                    await bot.send_video(
                        chat_id=chat_id,
                        video=item["media"],
                        caption=prompt or item.get("caption"),
                        reply_markup=keyboard,
                        parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
                    )
                # После отправки уже не надо отдельно текст
                prompt = None
            else:
                # 📚 Несколько медиа: сначала группа без клавиатуры
                group = []
                for item in media:
                    if item["type"] == "photo":
                        group.append(InputMediaPhoto(media=item["media"], caption=item.get("caption")))
                    elif item["type"] == "video":
                        group.append(InputMediaVideo(media=item["media"], caption=item.get("caption")))
                if group:
                    await bot.send_media_group(chat_id=chat_id, media=group)

        if files:
            for file_url in files:
                await bot.send_document(chat_id=chat_id, document=file_url)

        if prompt:
            await bot.send_message(
                chat_id=chat_id,
                text=prompt,
                reply_markup=keyboard,
                parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
            )

        if poll:
            await bot.send_poll(chat_id=chat_id, **poll)

    @staticmethod
    async def _reply_message(event, prompt, media, files, keyboard):
        if isinstance(event, CallbackQuery):
            event = event.message

        if media:
            if len(media) == 1:
                item = media[0]
                if item["type"] == "photo":
                    await event.reply_photo(
                        photo=item["media"],
                        caption=prompt or item.get("caption"),
                        reply_markup=keyboard,
                        parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
                    )
                elif item["type"] == "video":
                    await event.reply_video(
                        video=item["media"],
                        caption=prompt or item.get("caption"),
                        reply_markup=keyboard,
                        parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
                    )
                prompt = None
            else:
                for item in media:
                    if item["type"] == "photo":
                        await event.reply_photo(photo=item["media"])
                    elif item["type"] == "video":
                        await event.reply_video(video=item["media"])

        if files:
            for file_url in files:
                await event.reply_document(document=file_url)

        if prompt:
            await event.reply(
                text=prompt,
                reply_markup=keyboard,
                parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
            )

    @staticmethod
    async def _edit_message(event: CallbackQuery, prompt, keyboard):
        if not prompt:
            log.warning("No prompt provided for editing the message.")
            return

        try:
            if event.message.content_type != "text":
                # Если это не текстовое сообщение, нельзя редактировать — удаляем и отправляем новое
                await event.message.delete()
                await event.message.answer(
                    text=prompt,
                    reply_markup=keyboard,
                    parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
                )
            else:
                await event.message.edit_text(
                    text=prompt,
                    reply_markup=keyboard,
                    parse_mode=ReplyFactory.DEFAULT_PARSE_MODE,
                )
        except Exception as e:
            log.warning(f"Failed to edit message: {e}")

    @staticmethod
    async def _render_keyboard(options: dict) -> InlineKeyboardMarkup:
        # TODO: Сделать отдельную фабрику под клавиатуры
        buttons = []
        for key, value in options.items():
            button_text = value.get("text", key)
            callback_data = value.get("callback_data", key)
            buttons.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

        return InlineKeyboardMarkup(inline_keyboard=rows)

    @classmethod
    async def _prepare_config(cls, flow_config: dict, step_id: str) -> dict:
        flow_config = deepcopy(flow_config)

        if not flow_config.get("prompt"):
            flow_config["prompt"] = t(f"{step_id}.prompt")

        options = flow_config.get("options")
        if options:
            for key, option in options.items():
                if not option.get("text"):
                    option["text"] = t(f"{step_id}.options.{key}")

        poll = flow_config.get("poll")
        if poll:
            if not poll.get("question"):
                poll["question"] = t(f"{step_id}.poll.question")
            if "options" in poll:
                poll["options"] = [
                    t(f"{step_id}.poll.options.{i}", default=opt) if isinstance(opt, str) else opt
                    for i, opt in enumerate(poll["options"])
                ]

        return flow_config
