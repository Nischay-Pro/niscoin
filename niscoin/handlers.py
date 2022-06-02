from ctypes import Union
from typing import Any
from telegram import (
    Update,
)
import chat
import random
import time
import shlex
import commands
import sys
from constants import Reputation
from messages import Messages
from commands import _get_user_type, restricted_commands
from telegram.constants import ParseMode, ChatMemberStatus
from telegram.error import BadRequest
from misc import configure_levels


async def process_commands(update: Update, context: Any) -> None:
    """Process commands."""

    await check_configuration(context)

    if _is_bot_initated(update, context):
        try:
            if update.message.text.startswith("!"):
                await parse_command(update, context)
            else:
                if await handle_reputation(update, context) is None:
                    await reward_user(update, context)
        except AttributeError:
            return
    elif update.message.text == "!start":
        await parse_command(update, context)


async def reward_user(update: Update, context: Any) -> None:
    if await _is_message_bot(update, context):
        return
    current_user_id = update.message.from_user.id
    current_user = update.message.from_user.full_name
    current_chat_id = update.message.chat_id
    chat_configuration = context.chat_data["configuration"]
    if _check_user_exists(current_user_id, chat_configuration):
        user_epoch = _get_user_key(current_user_id, "last_message", chat_configuration)
        epoch_time = int(time.time())
        if (epoch_time - user_epoch) >= _get_user_key(
            current_user_id, "delta_award_time", chat_configuration
        ):
            random_xp = random.randint(1, 12)
            delta_award = random.randint(1 * 60, 4 * 60)
            if chat_configuration["configuration"]["lottery"]["enabled"]:
                odds = chat_configuration["configuration"]["lottery"]["odds"]
                multiplier = chat_configuration["configuration"]["lottery"][
                    "multiplier"
                ]
                if random.randint(1, odds) == 1:
                    random_xp *= multiplier
                    await context.bot.send_message(
                        text=f"7️⃣7️⃣7️⃣ Lucky message! {current_user} has received {random_xp} XP!",
                        chat_id=current_chat_id,
                    )
            _set_user_key(current_user_id, "xp", random_xp, chat_configuration, True)
            _set_user_key(
                current_user_id, "last_message", epoch_time, chat_configuration
            )
            _set_user_key(
                current_user_id, "delta_award_time", delta_award, chat_configuration
            )
    else:
        _create_user_data(current_user_id, chat_configuration)


async def handle_reputation(update: Update, context: Any) -> Any:
    current_user_id = update.message.from_user.id
    chat_configuration = context.chat_data["configuration"]
    if not chat_configuration["configuration"]["reputation"]["enabled"]:
        return

    if (
        current_user_id
        in context.chat_data["configuration"]["configuration"]["reputation"][
            "ignorelist"
        ]
    ):
        return

    if update.message.reply_to_message is None:
        return

    if update.message.reply_to_message.from_user.id == update.message.from_user.id:
        return
    filters_list = context.chat_data["configuration"]["configuration"]["reputation"][
        "filters"
    ]
    enabled_filters = tuple(
        filter(lambda x: filters_list[x]["enabled"], filters_list.keys())
    )
    reputation_triggers = {}
    reputation_list = []
    for filter_itm in enabled_filters:
        reputation_triggers[filter_itm] = filters_list[filter_itm]["base"]
        reputation_triggers[filter_itm].extend(filters_list[filter_itm]["custom"])
        reputation_list.extend(reputation_triggers[filter_itm])

    reputation_type = None
    if update.message.text in reputation_list:
        for reputation_itm in reputation_triggers.keys():
            if update.message.text in reputation_triggers[reputation_itm]:
                reputation_type = Reputation[reputation_itm.upper()]
                break

    if reputation_type is None:
        return

    reputation_modifier = reputation_type.value

    reply_user_id = update.message.reply_to_message.from_user.id
    chat_id = update.message.chat_id
    current_user = update.message.from_user.full_name
    reply_user = update.message.reply_to_message.from_user.full_name

    reputation_permissions = chat_configuration["configuration"]["reputation"][
        "adminOnly"
    ]
    user_type = await _get_user_type(update, context, current_user_id)
    if reputation_permissions and user_type not in restricted_commands:
        await context.bot.send_message(
            text=Messages.reputation_unauthorized.value,
            chat_id=chat_id,
            reply_to_message_id=update.message.message_id,
        )
        return

    if await _is_message_bot(update, context):
        return

    _ensure_user_exists(current_user_id, chat_configuration)
    _ensure_user_exists(reply_user_id, chat_configuration)

    chat_configuration["user_data"][str(reply_user_id)]["rep"] += reputation_modifier

    if abs(reputation_modifier) == 2:
        chat_configuration["user_data"][str(current_user_id)]["rep"] -= 1

    current_user_rep = _get_user_key(current_user_id, "rep", chat_configuration)
    reply_user_rep = _get_user_key(reply_user_id, "rep", chat_configuration)

    rep_positive = True if reputation_modifier > 0 else False
    if rep_positive:
        await context.bot.send_message(
            text=Messages.reputation_positive.value.format(
                user_give=current_user,
                user_give_rep=current_user_rep,
                user_receive=reply_user,
                user_receive_rep=reply_user_rep,
            ),
            chat_id=chat_id,
            parse_mode=ParseMode.HTML,
        )
    else:
        await context.bot.send_message(
            text=Messages.reputation_negative.value.format(
                user_give=current_user,
                user_give_rep=current_user_rep,
                user_receive=reply_user,
                user_receive_rep=reply_user_rep,
            ),
            chat_id=chat_id,
            parse_mode=ParseMode.HTML,
        )
    return True


def _is_bot_initated(update: Update, context: Any) -> bool:
    return context.chat_data["configuration"]["configuration"]["initiated"]


def _create_user_data(user_id: int, chat_configuration: dict) -> None:
    user_id = str(user_id)
    chat_configuration["user_data"][user_id] = chat.user_template(user_id)


def _set_user_key(
    user_id: int, key: str, value: int, chat_configuration: dict, append: bool = False
) -> None:
    user_id = str(user_id)
    if append:
        chat_configuration["user_data"][user_id][key] += value
    else:
        chat_configuration["user_data"][user_id][key] = value


def _get_user_key(user_id: int, key: str, chat_configuration: dict) -> int:
    user_id = str(user_id)
    return chat_configuration["user_data"][user_id][key]


def _check_user_exists(user_id: int, chat_configuration: dict) -> bool:
    user_id = str(user_id)
    if user_id in chat_configuration["user_data"].keys():
        return True
    else:
        return False


def _ensure_user_exists(user_id: int, chat_configuration: dict) -> None:
    if not _check_user_exists(user_id, chat_configuration):
        _create_user_data(user_id, chat_configuration)


async def _is_user_bot(
    user_id: int, chat_id: int, update: Update, context: Any
) -> bool:
    try:
        user_data = await context.bot.get_chat_member(chat_id, user_id)
        return user_data.user.is_bot
    except BadRequest:
        return True


async def _is_message_bot(update: Update, context: Any) -> bool:
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    if update.message.reply_to_message is not None:
        reply_user_id = update.message.reply_to_message.from_user.id
        if await _is_user_bot(reply_user_id, chat_id, update, context):
            return True

    return await _is_user_bot(user_id, chat_id, update, context)


def _extract_command_argument(message: str) -> str:
    message = message.lower().replace("!", "")
    try:
        message = shlex.split(message)
    except ValueError:
        return {"command": None, "argument": None}
    if len(message) == 1:
        return {"command": message[0], "arguments": []}
    else:
        return {"command": message[0], "arguments": message[1:]}


async def parse_command(update: Update, context: Any) -> None:
    args = _extract_command_argument(update.message.text)

    if await _is_message_bot(update, context):
        return

    if args["command"]:
        command = commands.supported_commands.get(args["command"], None)
        if command is not None:
            if args["command"] != "start":
                chat_configuration = context.chat_data["configuration"]
                _ensure_user_exists(update.message.from_user.id, chat_configuration)
                if update.message.reply_to_message is not None:
                    _ensure_user_exists(
                        update.message.reply_to_message.from_user.id, chat_configuration
                    )
            await command.execute(
                update=update, context=context, args=args["arguments"]
            )
        else:
            await context.bot.send_message(
                text=f"Command !{args['command']} not found!",
                chat_id=update.message.chat_id,
            )


async def check_configuration(context: Any) -> None:
    if "configuration" in context.chat_data.keys():
        chat_configuration = chat.from_dict(context.chat_data["configuration"])
        if chat.check_migration(chat_configuration):
            context.chat_data["configuration"] = chat.migrate_configuration(
                chat_configuration
            ).as_dict()
    else:
        if "init" in context.chat_data.keys():
            new_configuration = chat.migrate_legacy_user_data(
                context.chat_data, chat.ChatConfiguration()
            )
            del context.chat_data["init"]
            del context.chat_data["duels"]
            del context.chat_data["users"]
            await configure_levels(None, context)
            context.chat_data["configuration"] = new_configuration.as_dict()
        else:
            context.chat_data["configuration"] = chat.ChatConfiguration().as_dict()
