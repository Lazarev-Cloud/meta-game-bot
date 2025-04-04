"""
ReplyFactory module for building and sending Telegram messages in a flexible way.

This module provides a universal factory class `ReplyFactory` that handles:
- Sending new messages
- Replying to user messages
- Editing previous bot messages
- Sending media (photo, video)
- Sending multiple media as a media group
- Sending files and polls
- Attaching inline keyboards
- Auto-filling missing prompts and button texts using localization

Supported formats:
- Text messages (with parse mode)
- Single media (photo/video) with caption and keyboard
- Media groups
- Polls (with localized questions and options)

The factory is designed to maximize the compactness of messages, automatically
combining text and media where possible, and fallback-resilient if edits fail.
"""
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
    """
    Factory for sending different types of replies based on flow configuration.

    Supports new messages, replies, message edits, sending media, files, polls, and keyboards.
    """

    DEFAULT_PARSE_MODE = "HTML"

    @classmethod
    async def send(cls, event: Message | CallbackQuery, state: FSMContext, flow_config: dict, step_id: str) -> None:
        """
        Send a message, media, poll, or file according to flow configuration.

        Args:
            event (Message | CallbackQuery): Incoming user event.
            state (FSMContext): FSM context.
            flow_config (dict): Configuration of the current flow step.
            step_id (str): Identifier of the current step.
        """
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

        # Choose the appropriate way to send the reply
        if reply_type == "edit" and isinstance(event, CallbackQuery):
            if not preserve_message:
                await cls._delete_message(event)
                await cls._send_all(bot, chat_id, prompt, media, files, poll, keyboard)
            else:
                await cls._edit_message(event, prompt, keyboard)
        elif reply_type == "reply":
            await cls._reply_message(event, prompt, media, files, keyboard)
        else:  # "new"
            await cls._send_all(bot, chat_id, prompt, media, files, poll, keyboard)

    @staticmethod
    async def _delete_message(event: CallbackQuery):
        """
        Delete a previous bot message.

        Args:
            event (CallbackQuery): Callback event to delete message from.
        """
        try:
            await event.message.delete()
        except Exception as e:
            log.warning(f"Failed to delete message: {e}")

    @staticmethod
    async def _send_all(bot, chat_id, prompt, media, files, poll, keyboard):
        """
        Send all available content: media, files, text, and poll.

        Args:
            bot (Bot): Telegram Bot instance.
            chat_id (int): Chat ID to send the message to.
            prompt (str): Text prompt.
            media (list): List of media items.
            files (list): List of files to send.
            poll (dict): Poll configuration.
            keyboard (InlineKeyboardMarkup): Inline keyboard to attach.
        """
        if media:
            if len(media) == 1:
                # 📷 Single media: attach prompt and keyboard
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
                # No need to send prompt separately
                prompt = None
            else:
                # 📚 Multiple media: send media group without prompt
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
        """
        Reply to the user's message.

        Args:
            event (Message): User's message or converted CallbackQuery.
            prompt (str): Text prompt.
            media (list): List of media items.
            files (list): List of file URLs.
            keyboard (InlineKeyboardMarkup): Inline keyboard to attach.
        """
        if isinstance(event, CallbackQuery):
            event = event.message  # Convert to Message for easier work

        if media:
            if len(media) == 1:
                # 📷 Single media
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
                # 📚 Multiple media without prompt
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
        """
        Edit an existing bot message or delete and resend if editing is impossible.

        Args:
            event (CallbackQuery): Event to edit the message.
            prompt (str): New text prompt.
            keyboard (InlineKeyboardMarkup): New inline keyboard.
        """
        if not prompt:
            log.warning("No prompt provided for editing the message.")
            return

        try:
            if event.message.content_type != "text":
                # Cannot edit non-text message, delete and send a new one
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
        """
        Render inline keyboard based on flow options.

        Args:
            options (dict): Dictionary of button options.

        Returns:
            InlineKeyboardMarkup: Rendered inline keyboard.
        """
        # TODO: Move to a separate KeyboardFactory later
        buttons = []
        for key, value in options.items():
            button_text = value.get("text", key)
            callback_data = value.get("callback_data", key)
            buttons.append(InlineKeyboardButton(text=button_text, callback_data=callback_data))

        # Group buttons into rows of 2
        rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

        return InlineKeyboardMarkup(inline_keyboard=rows)

    @classmethod
    async def _prepare_config(cls, flow_config: dict, step_id: str) -> dict:
        """
        Prepare and enrich the flow configuration by filling missing prompt, options, and poll texts.

        Args:
            flow_config (dict): Original flow configuration.
            step_id (str): Current step ID.

        Returns:
            dict: Enriched flow configuration.
        """
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
