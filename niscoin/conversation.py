from typing import Any
from misc import configure_levels
from help import help_strings, get_back_keyboard, get_help_keyboard
from handlers import process_commands
from telegram import (
    Update,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode, ChatType
from telegram.error import BadRequest
import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

back_keyboard = get_back_keyboard()
help_keyboard = get_help_keyboard()

help_main = """
Help

Hello\! I am `niscoin`, a bot that allows you to game\-ify your group chats\.
I support a number of commands, which are listed below\. 
If you find any bugs or have any suggestions, please visit my [GitHub repo page](https://github.com/Nischay\-Pro/niscoin)

All commands can be used with the following \! prefix\.
"""


async def error(update: Update, context: Any) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)


async def start(update: Update, context: Any) -> None:
    """Send a message when the command /start is issued."""

    await configure_levels(update, context)
    await update.message.reply_text(
        "Type `!start` to begin", parse_mode=ParseMode.MARKDOWN_V2
    )


async def help_button(update: Update, context: Any) -> None:
    query = update.callback_query

    await query.answer()

    if query.data == "back":
        await query.edit_message_text(
            text=help_main,
            reply_markup=InlineKeyboardMarkup(help_keyboard),
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )
    else:
        text = f"""
        {help_strings[query.data].keyboard_text}  `{help_strings[query.data].command}`
        {help_strings[query.data].description}
        """
        try:
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(back_keyboard),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except BadRequest:
            pass


async def help(update: Update, context: Any) -> None:
    """Send a message when the command /help is issued."""

    if update.effective_chat.type != ChatType.PRIVATE:
        await update.message.reply_text(
            "Help is accessible only from a private chat. DM this bot to get help."
        )
        return

    reply_markup = InlineKeyboardMarkup(help_keyboard)
    await update.message.reply_text(
        text=help_main,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


async def echo(update: Update, context: Any) -> None:
    """Echo the user message."""

    # Check if the user is in a group chat
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            "Niscoin is a group-only bot. Please run it in a group chat."
        )
    else:
        await process_commands(update, context)
