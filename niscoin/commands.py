from email import message
from lib2to3.pytree import Base
from help import help_strings
from messages import Messages
import sys
import inspect
from misc import (
    get_level_from_xp,
    booleanify,
    boolean_to_user,
    match_only_alphanumeric,
)
from constants import Award, CliStoreType, Reputation
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import BadRequest
import tempfile
from gtts import gTTS, lang
import os
import textwrap

supported_tts_languages = lang.tts_langs()


async def _get_user_name(update, context, user_id, chat_id):
    try:
        user_data = await context.bot.get_chat_member(chat_id, user_id)
    except BadRequest:
        return None
    user_first_name = user_data.user.first_name
    user_last_name = user_data.user.last_name

    if user_last_name is None:
        user_last_name = ""

    return {
        "first_name": user_first_name,
        "last_name": user_last_name,
    }


async def _get_user_type(update, context, user_id):
    user_data = await context.bot.get_chat_member(update.message.chat_id, user_id)
    user_type = user_data.status

    return user_type


def _type_base_command(value):
    try:
        value.__command__
        return True
    except AttributeError:
        return False


def _is_type_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_positive(value):
    try:
        if int(value) > 0:
            return True
        else:
            return False
    except ValueError:
        return False


restricted_commands = (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


class BaseCommand:
    def __init__(self, name="base"):
        self.name = name

    def execute(self, context=None, update=None, args=None):
        raise NotImplementedError

    def help(self):
        try:
            return help_strings[self.name].description
        except KeyError:
            raise NotImplementedError(f"Help for command {self.name} not found")

    def __str__(self):
        return self.name

    def __command__(self):
        return True


class StartCommand(BaseCommand):
    def __init__(self):
        super().__init__("start")

    async def execute(self, context=None, update=None, args=None):
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        if not await _get_user_type(update, context, user_id) in ChatMemberStatus.OWNER:
            await context.bot.send_message(
                text=Messages.unauthorized_admin.value,
                chat_id=chat_id,
                reply_to_message_id=message_id,
            )
            return

        if context.chat_data["configuration"]["configuration"]["initiated"]:
            await context.bot.send_message(
                text=Messages.initate_fail.value,
                chat_id=chat_id,
                reply_to_message_id=message_id,
            )
            return
        else:
            context.chat_data["configuration"]["configuration"]["initiated"] = True
            await context.bot.send_message(
                text=Messages.initate_success.value,
                chat_id=chat_id,
                reply_to_message_id=message_id,
            )


class TopCoinsCommand(BaseCommand):
    def __init__(self):
        super().__init__("topcoins")

    async def execute(self, update=None, context=None, args=None):
        chat_text = "The current Coins table: \n"
        chat_id = update.message.chat_id
        users = context.chat_data["configuration"]["user_data"]
        users_sorted = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)
        for idx, user in enumerate(users_sorted[0:10]):
            try:
                user_name = await _get_user_name(update, context, user[0], chat_id)
                chat_text += f'{idx + 1}. <a href="tg://user?id={user[0]}">{user_name["first_name"]} {user_name["last_name"]}</a> ({user[1]["coins"]})\n'
            except KeyError:
                pass
        await context.bot.send_message(
            chat_id=chat_id, text=chat_text, parse_mode="HTML"
        )


class TopReputationCommand(BaseCommand):
    def __init__(self):
        super().__init__("toprep")

    async def execute(self, update=None, context=None, args=None):
        chat_text = "The current Reputation table: \n"
        chat_id = update.message.chat_id
        users = context.chat_data["configuration"]["user_data"]
        users_sorted = sorted(users.items(), key=lambda x: x[1]["rep"], reverse=True)
        for idx, user in enumerate(users_sorted[0:10]):
            try:
                user_name = await _get_user_name(update, context, user[0], chat_id)
                award = ""
                if idx < 3:
                    award = list(Award)[idx].value
                chat_text += f'{idx + 1}. <a href="tg://user?id={user[0]}">{user_name["first_name"]} {user_name["last_name"]}</a> ({user[1]["rep"]}) {award}\n'
            except KeyError:
                pass
        await context.bot.send_message(
            chat_id=chat_id, text=chat_text, parse_mode="HTML"
        )


class TopXPCommand(BaseCommand):
    def __init__(self):
        super().__init__("topxp")

    async def execute(self, update=None, context=None, args=None):
        chat_text = "The current XP table: \n"
        chat_id = update.message.chat_id
        users = context.chat_data["configuration"]["user_data"]
        users_sorted = sorted(users.items(), key=lambda x: x[1]["xp"], reverse=True)
        for idx, user in enumerate(users_sorted[0:10]):
            try:
                user_name = await _get_user_name(update, context, user[0], chat_id)
                user_xp = user[1]["xp"]
                levels = context.bot_data["configuration"]["levels"]
                user_level = get_level_from_xp(user_xp, levels)
                user_level_bound = levels[user_level]
                award = ""
                if idx < 3:
                    award = list(Award)[idx].value
                chat_text += f'{idx + 1}. <a href="tg://user?id={user[0]}">{user_name["first_name"]} {user_name["last_name"]}</a> ({user_xp} / {user_level_bound}) - Level {user_level} {award}\n'
            except KeyError:
                pass
        await context.bot.send_message(
            chat_id=chat_id, text=chat_text, parse_mode="HTML"
        )


class ExchangeCommand(BaseCommand):
    def __init__(self):
        super().__init__("exchange")

    async def execute(self, context=None, update=None, args=None):
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        current_user_xp = context.chat_data["configuration"]["user_data"][str(user_id)][
            "xp"
        ]
        current_exchange_rate = context.chat_data["configuration"]["configuration"][
            "coins"
        ]["exchangeRate"]

        if not context.chat_data["configuration"]["configuration"]["coins"]["enabled"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.coins_disabled.value,
                reply_to_message_id=message_id,
            )
            return

        if len(args) == 1:
            if _is_type_int(args[0]) and _is_positive(args[0]):
                coins_to_exchange = int(args[0])
                if coins_to_exchange * current_exchange_rate > current_user_xp:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=Messages.exchange_not_enough.value,
                        reply_to_message_id=message_id,
                    )
                    return
                else:
                    new_user_xp = current_user_xp - (
                        coins_to_exchange * current_exchange_rate
                    )
                    context.chat_data["configuration"]["user_data"][str(user_id)][
                        "xp"
                    ] = new_user_xp
                    context.chat_data["configuration"]["user_data"][str(user_id)][
                        "coins"
                    ] += coins_to_exchange
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=Messages.exchange_success.value,
                        reply_to_message_id=message_id,
                    )
                    return
            elif args[0] == "rate":
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=Messages.exchange_cost.value.format(
                        cost=current_exchange_rate
                    ),
                    reply_to_message_id=message_id,
                )
                return
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=Messages.exchange_invalid.value,
                    reply_to_message_id=message_id,
                )
                return
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.exchange_invalid.value,
                reply_to_message_id=message_id,
            )
            return


class GiveCoinsCommand(BaseCommand):
    def __init__(self):
        super().__init__("give")

    async def execute(self, context=None, update=None, args=None):

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        current_user_coins = context.chat_data["configuration"]["user_data"][
            str(user_id)
        ]["coins"]

        if not context.chat_data["configuration"]["configuration"]["coins"]["enabled"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.coins_disabled.value,
                reply_to_message_id=message_id,
            )
            return

        if update.message.reply_to_message is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.give_noreply.value,
                reply_to_message_id=message_id,
            )
            return

        if update.message.reply_to_message.from_user.id == user_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.self_not_allowed.value,
                reply_to_message_id=message_id,
            )
            return

        if len(args) == 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.give_invalid.value,
                reply_to_message_id=message_id,
            )
            return

        elif len(args) == 1:
            if _is_type_int(args[0]) and _is_positive(args[0]):
                coins_to_give = int(args[0])
                if coins_to_give > current_user_coins:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=Messages.give_insufficient.value,
                        reply_to_message_id=message_id,
                    )
                    return
                else:
                    context.chat_data["configuration"]["user_data"][str(user_id)][
                        "coins"
                    ] -= coins_to_give
                    context.chat_data["configuration"]["user_data"][
                        str(update.message.reply_to_message.from_user.id)
                    ]["coins"] += coins_to_give
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=Messages.give_success.value.format(
                            amount=coins_to_give,
                            user=update.message.reply_to_message.from_user.first_name,
                        ),
                        reply_to_message_id=message_id,
                    )
                    return

            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=Messages.give_invalid.value,
                    reply_to_message_id=message_id,
                )
                return

        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.give_invalid.value,
                reply_to_message_id=message_id,
            )
            return


class GetCoinsCommand(BaseCommand):
    def __init__(self):
        super().__init__("getcoins")

    async def execute(self, context=None, update=None, args=None):

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        current_user_coins = context.chat_data["configuration"]["user_data"][
            str(user_id)
        ]["coins"]

        if not context.chat_data["configuration"]["configuration"]["coins"]["enabled"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.coins_disabled.value,
                reply_to_message_id=message_id,
            )
            return

        await context.bot.send_message(
            chat_id=chat_id,
            text=Messages.get_coins.value.format(coins=current_user_coins),
            reply_to_message_id=message_id,
        )
        return


class GetXPCommand(BaseCommand):
    def __init__(self):
        super().__init__("getxp")

    async def execute(self, context=None, update=None, args=None):

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        current_user_xp = context.chat_data["configuration"]["user_data"][str(user_id)][
            "xp"
        ]

        xp_levels = context.bot_data["configuration"]["levels"]

        await context.bot.send_message(
            chat_id=chat_id,
            text=Messages.get_xp.value.format(
                xp=current_user_xp, level=get_level_from_xp(current_user_xp, xp_levels)
            ),
            reply_to_message_id=message_id,
        )
        return


class GetReputationCommand(BaseCommand):
    def __init__(self):
        super().__init__("getrep")

    async def execute(self, context=None, update=None, args=None):

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        current_user_reputation = context.chat_data["configuration"]["user_data"][
            str(user_id)
        ]["rep"]

        await context.bot.send_message(
            chat_id=chat_id,
            text=Messages.get_reputation.value.format(
                reputation=current_user_reputation
            ),
            reply_to_message_id=message_id,
        )
        return


class SetCoinsCommand(BaseCommand):
    def __init__(self):
        super().__init__("setcoins")

    async def execute(self, context=None, update=None, args=None):

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        if not context.chat_data["configuration"]["configuration"]["coins"]["enabled"]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.coins_disabled.value,
                reply_to_message_id=message_id,
            )
            return

        reply_user_id = update.message.reply_to_message.from_user.id

        if not await _get_user_type(update, context, user_id) in restricted_commands:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.unauthorized_user.value,
                reply_to_message_id=message_id,
            )
            return

        if update.message.reply_to_message is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_coins_noreply.value,
                reply_to_message_id=message_id,
            )
            return

        if len(args) == 1 and _is_type_int(args[0]) and _is_positive(args[0]):
            context.chat_data["configuration"]["user_data"][str(reply_user_id)][
                "coins"
            ] = int(args[0])
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_coins_success.value,
                reply_to_message_id=message_id,
            )
            return
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_coins_invalid.value,
                reply_to_message_id=message_id,
            )
            return


class SetXPCommand(BaseCommand):
    def __init__(self):
        super().__init__("setxp")

    async def execute(self, context=None, update=None, args=None):

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        if not await _get_user_type(update, context, user_id) in restricted_commands:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.unauthorized_user.value,
                reply_to_message_id=message_id,
            )
            return

        if update.message.reply_to_message is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_xp_noreply.value,
                reply_to_message_id=message_id,
            )
            return

        reply_user_id = update.message.reply_to_message.from_user.id

        if len(args) == 1 and _is_type_int(args[0]) and _is_positive(args[0]):
            context.chat_data["configuration"]["user_data"][str(reply_user_id)][
                "xp"
            ] = int(args[0])
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_xp_success.value,
                reply_to_message_id=message_id,
            )
            return
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_xp_invalid.value,
                reply_to_message_id=message_id,
            )
            return


class SetReputationCommand(BaseCommand):
    def __init__(self):
        super().__init__("setrep")

    async def execute(self, context=None, update=None, args=None):

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        if not await _get_user_type(update, context, user_id) in restricted_commands:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.unauthorized_user.value,
                reply_to_message_id=message_id,
            )
            return

        if update.message.reply_to_message is None:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_rep_noreply.value,
                reply_to_message_id=message_id,
            )
            return

        reply_user_id = update.message.reply_to_message.from_user.id

        if len(args) == 1 and _is_type_int(args[0]) and _is_positive(args[0]):
            context.chat_data["configuration"]["user_data"][str(reply_user_id)][
                "rep"
            ] = int(args[0])
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_rep_success.value,
                reply_to_message_id=message_id,
            )
            return
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.set_rep_invalid.value,
                reply_to_message_id=message_id,
            )
            return


class PlayCommand(BaseCommand):
    def __init__(self):
        super().__init__("play")

    async def parse_tts(self, context=None, update=None, args=None):
        if args[0] in ["lang", "language", "l"]:
            text = "Supported languages are:\n\n"
            for lang in supported_tts_languages.keys():
                text += f"{lang} → {supported_tts_languages[lang]}" + "\n"
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=text,
                reply_to_message_id=update.message.message_id,
            )
            return None

        if args[0] in ["cost"]:
            tts_cost = context.chat_data["configuration"]["configuration"][
                "translation"
            ]["cost"]
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=Messages.translation_cost.value.format(cost=tts_cost),
                reply_to_message_id=update.message.message_id,
            )
            return None

        if args[0] not in supported_tts_languages.keys():
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=Messages.translation_invalid_language.value,
                reply_to_message_id=update.message.message_id,
            )
            return None

        try:
            slow_mode = booleanify(args[1])
        except ValueError:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=Messages.translation_invalid_slow_mode.value,
                reply_to_message_id=update.message.message_id,
            )
            return None

        if update.message.reply_to_message is None:
            try:
                tts_message = args[2]
            except IndexError:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.translation_no_message.value,
                    reply_to_message_id=update.message.message_id,
                )
                return None
        else:
            tts_message = update.message.reply_to_message.text

        return {
            "language": args[0],
            "slow_mode": slow_mode,
            "message": tts_message,
        }

    async def execute(self, context=None, update=None, args=None):
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id
        message_id = update.message.message_id

        if not context.chat_data["configuration"]["configuration"]["translation"][
            "enabled"
        ]:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.translation_disabled.value,
                reply_to_message_id=message_id,
            )
            return

        user_coins = context.chat_data["configuration"]["user_data"][str(user_id)][
            "coins"
        ]
        tts_cost = context.chat_data["configuration"]["configuration"]["translation"][
            "cost"
        ]

        if len(args) == 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=Messages.translation_no_message.value,
                reply_to_message_id=message_id,
            )
            return
        elif len(args) > 0:
            tts_options = await self.parse_tts(context, update, args)
            if tts_options is None:
                return

            if len(tts_options["message"]) > 1000:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=Messages.translation_max_length.value,
                    reply_to_message_id=message_id,
                )
                return

            else:
                if user_coins < tts_cost:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=Messages.translation_not_enough_coins.value,
                        reply_to_message_id=message_id,
                    )
                    return
                tts_output = gTTS(
                    tts_options["message"],
                    lang=tts_options["language"],
                    slow=tts_options["slow_mode"],
                )
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_file = os.path.join(tmp_dir, "tts.mp3")
                    tts_output.save(tmp_file)
                    await context.bot.send_voice(
                        chat_id=chat_id,
                        voice=open(tmp_file, "rb"),
                        reply_to_message_id=message_id,
                    )
                    context.chat_data["configuration"]["user_data"][str(user_id)][
                        "coins"
                    ] -= tts_cost
                    return


class GetFiltersCommand(BaseCommand):
    def __init__(self):
        super().__init__("getfilters")

    async def execute(self, context=None, update=None, args=None):
        chat_id = update.message.chat_id
        message_id = update.message.message_id

        filters_list = context.chat_data["configuration"]["configuration"][
            "reputation"
        ]["filters"]
        enabled_filters = tuple(
            filter(lambda x: filters_list[x]["enabled"], filters_list.keys())
        )
        disabled_filters = set(filters_list.keys()) - set(enabled_filters)

        text = "<b>Currently enabled reputation filters: </b>\n"
        for idx, filter_name in enumerate(enabled_filters):
            filter_triggers = (
                filters_list[filter_name]["base"] + filters_list[filter_name]["custom"]
            )
            filter_triggers = ", ".join(filter_triggers)
            text += f"{idx + 1}. {filter_name} → {filter_triggers}\n"

        if len(disabled_filters) > 0:
            text += "\n<b>Currently disabled reputation filters: </b>\n"
            for idx, filter_name in enumerate(disabled_filters):
                text += f"{idx + 1}. {filter_name}\n"

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_to_message_id=message_id,
            parse_mode=ParseMode.HTML,
        )
        return


class CliCommand(BaseCommand):
    def __init__(self):
        super().__init__("cli")

    help_text_main = """
    <b>Usage:</b> !cli [ OBJECT ] [ OPTIONS ] [ ARGUMENTS ]

    <b>Where:</b>
    OPTIONS :- { set | get | add | remove | list }
    OBJECT :- { coins | reputation | lottery | translation | filters }
    
    <b>Description:</b>
    <b>coins</b> :- Configure the bot's coin system, including the XP to coin exchange rate.
    <b>reputation</b> :- Configure the bot's reputation system and the permissions of who
    can give and take reputation.
    <b>lottery</b> :- Configure the bot's XP lottery system, including the probability and
    multiplier.
    <b>translation</b> :- Configure the bot's text to speech system and the cost for each
    TTS request.
    <b>filters</b> :- Configure the bot's reputation filters, including enabling and disabling
    individual filters. You can also view the status of all filters and add
    or remove new filter triggers."""

    help_text_coins = """
    <b>Usage:</b>

    !cli coins [ set | get ] [ enabled | disabled ]
    !cli coins [ set | get ] [ exchange / rate ] [ amount ]"""

    help_text_lottery = """
    <b>Usage:</b>
    
    !cli lottery [ set | get ] [ enabled | disabled ]
    !cli lottery odds [ set | get ] [ amount ]
    !cli lottery multipler [ set | get ] [ amount ]"""

    help_text_translation = """
    <b>Usage:</b>

    !cli [ translation / tts ] [ set | get ] [ enabled | disabled ]
    !cli [ translation / tts ] cost [ set | get ] [ amount ]"""

    help_text_reputation = """
    <b>Usage:</b>
    
    !cli reputation [ set | get ] [ enabled | disabled ]
    !cli reputation adminOnly [ set | get ] [ enabled | disabled ]
    !cli reputation ignoreList [ add | remove ] ( As a reply to the user to ignore)
    !cli reputation ignoreList [ add | remove ] [@user]"""

    help_text_filters = """
    <b>Usage:</b>
    
    !cli filters [ get ]
    !cli filters [ filter_name ] [ set | get ] [ enabled | disabled ]
    !cli filters [ filter_name ] custom [ add | remove | list ] [ trigger ]"""

    async def invalid_option(self, context=None, update=None):
        chat_id = update.message.chat_id
        message_id = update.message.message_id

        await context.bot.send_message(
            chat_id=chat_id,
            text=Messages.cli_invalid.value,
            reply_to_message_id=message_id,
        )
        return

    async def coin_handler(self, context=None, update=None, args=None):
        if len(args) == 0 or args[0] == "help":
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=textwrap.dedent(self.help_text_coins),
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        else:
            if args[0] == "set" and len(args) > 1:
                if args[1] == "enabled":
                    context.chat_data["configuration"]["configuration"]["coins"][
                        "enabled"
                    ] = True
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                elif args[1] == "disabled":
                    context.chat_data["configuration"]["configuration"]["coins"][
                        "enabled"
                    ] = False
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                else:
                    await self.invalid_option(context, update)
                    return

            elif args[0] == "get":
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=boolean_to_user(
                        context.chat_data["configuration"]["configuration"]["coins"][
                            "enabled"
                        ]
                    ),
                    reply_to_message_id=update.message.message_id,
                )
                return
            elif args[0] in ("rate", "exchange"):
                await self.int_handler(context, update, args[1:], CliStoreType.EXCHANGE)
                return
            else:
                await self.invalid_option(context, update)
                return

    async def lottery_handler(self, context=None, update=None, args=None):
        if len(args) == 0 or args[0] == "help":
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=textwrap.dedent(self.help_text_lottery),
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        else:
            if args[0] == "set" and len(args) > 1:
                if args[1] == "enabled":
                    context.chat_data["configuration"]["configuration"]["lottery"][
                        "enabled"
                    ] = True
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                elif args[1] == "disabled":
                    context.chat_data["configuration"]["configuration"]["lottery"][
                        "enabled"
                    ] = False
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                else:
                    await self.invalid_option(context, update)
                    return
            elif args[0] == "get":
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=boolean_to_user(
                        context.chat_data["configuration"]["configuration"]["lottery"][
                            "enabled"
                        ]
                    ),
                    reply_to_message_id=update.message.message_id,
                )
                return
            elif args[0] == "odds":
                await self.int_handler(
                    context, update, args[1:], store=CliStoreType.ODDS
                )
                return
            elif args[0] == "multiplier":
                await self.int_handler(
                    context, update, args[1:], store=CliStoreType.MULTIPLIER
                )
                return
            else:
                await self.invalid_option(context, update)
                return

    async def reputation_ignore_handler(self, context=None, update=None, args=None):
        chat_id = update.message.chat_id
        if len(args) == 0:
            await self.invalid_option(context, update)
            return
        elif (len(args) == 2 and args[0] in ("add", "remove")) or (
            len(args) == 1
            and args[0] in ("add", "remove")
            and update.message.reply_to_message is not None
        ):
            user_list = context.chat_data["configuration"]["configuration"][
                "reputation"
            ]["ignorelist"]
            if update.message.reply_to_message is None:
                try:
                    user_id = int(args[1])
                except ValueError:
                    await self.invalid_option(context, update)
                    return
            else:
                user_id = update.message.reply_to_message.from_user.id
            if user_id in user_list:
                user_name = await _get_user_name(update, context, user_id, chat_id)
                if args[0] == "add":
                    text = Messages.cli_user_already_ignored.value.format(
                        user=user_name["first_name"]
                    )
                else:
                    user_list.remove(user_id)
                    text = Messages.cli_user_removed.value.format(
                        user=user_name["first_name"]
                    )

                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=text,
                    reply_to_message_id=update.message.message_id,
                )
                return
            else:
                user_name = await _get_user_name(update, context, user_id, chat_id)
                if user_name is None:
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_user_does_not_exist.value.format(
                            user=user_id
                        ),
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                else:
                    if args[0] == "add":
                        user_list.append(user_id)
                        text = Messages.cli_user_added.value.format(
                            user=user_name["first_name"]
                        )
                    else:
                        text = Messages.cli_user_not_in_ignore_list.value.format(
                            user=user_name["first_name"]
                        )
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=text,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
        elif args[0] == "list":
            user_list = context.chat_data["configuration"]["configuration"][
                "reputation"
            ]["ignorelist"]
            if len(user_list) == 0:
                text = Messages.cli_ignore_list_empty.value
            else:
                text = "Users in ignore list:\n"
                for user_id in user_list.copy():
                    user_name = await _get_user_name(update, context, user_id, chat_id)
                    try:
                        text += f'→ <a href="tg://user?id={user_id}">{user_name["first_name"]} {user_name["last_name"]}</a>\n'
                    except (KeyError, TypeError):
                        user_list.remove(user_id)
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=text,
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        else:
            await self.invalid_option(context, update)
            return

    async def reputation_handler(self, context=None, update=None, args=None):
        if len(args) == 0 or args[0] == "help":
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=textwrap.dedent(self.help_text_reputation),
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        else:
            if args[0] == "set" and len(args) > 1:
                if args[1] == "enabled":
                    context.chat_data["configuration"]["configuration"]["reputation"][
                        "enabled"
                    ] = True
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                elif args[1] == "disabled":
                    context.chat_data["configuration"]["configuration"]["reputation"][
                        "enabled"
                    ] = False
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                else:
                    await self.invalid_option(context, update)
                    return
            elif args[0] == "get":
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=boolean_to_user(
                        context.chat_data["configuration"]["configuration"][
                            "reputation"
                        ]["enabled"]
                    ),
                    reply_to_message_id=update.message.message_id,
                )
                return
            elif args[0] == "adminonly":
                if args[1] == "get":
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=boolean_to_user(
                            context.chat_data["configuration"]["configuration"][
                                "reputation"
                            ]["adminOnly"]
                        ),
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                elif args[1] == "set":
                    if args[2] == "enabled":
                        context.chat_data["configuration"]["configuration"][
                            "reputation"
                        ]["adminOnly"] = True
                        await context.bot.send_message(
                            chat_id=update.message.chat_id,
                            text=Messages.cli_success.value,
                            reply_to_message_id=update.message.message_id,
                        )
                        return
                    elif args[2] == "disabled":
                        context.chat_data["configuration"]["configuration"][
                            "reputation"
                        ]["adminOnly"] = False
                        await context.bot.send_message(
                            chat_id=update.message.chat_id,
                            text=Messages.cli_success.value,
                            reply_to_message_id=update.message.message_id,
                        )
                        return
                    else:
                        await self.invalid_option(context, update)
                        return
            elif args[0] == "ignorelist":
                await self.reputation_ignore_handler(context, update, args[1:])
                return
            else:
                await self.invalid_option(context, update)
                return

    async def translation_handler(self, context=None, update=None, args=None):
        if len(args) == 0 or args[0] == "help":
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=textwrap.dedent(self.help_text_translation),
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        else:
            if args[0] == "set" and len(args) > 1:
                if args[1] == "enabled":
                    context.chat_data["configuration"]["configuration"]["translation"][
                        "enabled"
                    ] = True
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                elif args[1] == "disabled":
                    context.chat_data["configuration"]["configuration"]["translation"][
                        "enabled"
                    ] = False
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_success.value,
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                else:
                    await self.invalid_option(context, update)
                    return
            elif args[0] == "get":
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=boolean_to_user(
                        context.chat_data["configuration"]["configuration"][
                            "translation"
                        ]["enabled"]
                    ),
                    reply_to_message_id=update.message.message_id,
                )
                return
            elif args[0] in "cost":
                await self.int_handler(
                    context, update, args[1:], CliStoreType.TRANSLATION
                )
                return
            else:
                await self.invalid_option(context, update)
                return

    async def reputation_filter_handler(
        self, context=None, update=None, args=None, reputation_filter=None
    ):
        filter_dict = context.chat_data["configuration"]["configuration"]["reputation"][
            "filters"
        ]
        reputation_list = []
        for filter_itm in filter_dict:
            reputation_list.extend(filter_dict[filter_itm]["base"])
            reputation_list.extend(filter_dict[filter_itm]["custom"])
        if args[0] == "list":
            rep_filters_base = context.chat_data["configuration"]["configuration"][
                "reputation"
            ]["filters"][reputation_filter.name.lower()]["base"]
            rep_filters_custom = context.chat_data["configuration"]["configuration"][
                "reputation"
            ]["filters"][reputation_filter.name.lower()]["custom"]
            text = f"Currently active trigger words for {reputation_filter.name.lower()}:\n"
            text += "<b>Base triggers:</b>\n"
            for word in rep_filters_base:
                text += f"→ <b>{word}</b>\n"
            text += "<b>Custom triggers:</b>\n"
            if len(rep_filters_custom) == 0:
                text += "None configured\n"
            else:
                for word in rep_filters_custom:
                    text += f"→ <b>{word}</b>\n"
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=text,
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        elif len(args) == 2 and args[0] == "add":
            custom_word = args[1]
            if custom_word in reputation_list:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.cli_filter_word_exists.value.format(word=custom_word),
                    reply_to_message_id=update.message.message_id,
                )
                return
            else:
                if not match_only_alphanumeric(custom_word):
                    await context.bot.send_message(
                        chat_id=update.message.chat_id,
                        text=Messages.cli_filter_word_invalid_characters.value.format(
                            word=custom_word
                        ),
                        reply_to_message_id=update.message.message_id,
                    )
                    return
                context.chat_data["configuration"]["configuration"]["reputation"][
                    "filters"
                ][reputation_filter.name.lower()]["custom"].append(custom_word)
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.cli_filter_word_added.value.format(word=custom_word),
                    reply_to_message_id=update.message.message_id,
                )
                return
        elif len(args) == 2 and args[0] == "remove":
            custom_word = args[1]
            if custom_word in reputation_list:
                context.chat_data["configuration"]["configuration"]["reputation"][
                    "filters"
                ][reputation_filter.name.lower()]["custom"].remove(custom_word)
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.cli_filter_word_removed.value.format(
                        word=custom_word
                    ),
                    reply_to_message_id=update.message.message_id,
                )
                return
            else:
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.cli_filter_word_does_not_exist.value.format(
                        word=custom_word
                    ),
                    reply_to_message_id=update.message.message_id,
                )
                return
        else:
            await self.invalid_option(context, update)
            return
        return

    async def filters_handler(self, context=None, update=None, args=None, store=None):
        if len(args) == 0 or args[0] == "help":
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=textwrap.dedent(self.help_text_filters),
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        elif len(args) == 1 and args[0] == "get":
            filters = context.chat_data["configuration"]["configuration"]["reputation"][
                "filters"
            ].keys()
            text = "Reputation Filters available:\n"
            for idx, filter in enumerate(filters):
                filter_status = boolean_to_user(
                    context.chat_data["configuration"]["configuration"]["reputation"][
                        "filters"
                    ][filter]["enabled"]
                )
                filter_value = Reputation[filter.upper()].value
                text += f"{idx + 1}. {filter.title()} ({filter_value}) → <b>{filter_status}</b>\n"
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=text,
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        elif len(args) == 2 and args[1] == "get":
            try:
                filter = Reputation[args[0].upper()]
            except KeyError:
                await self.invalid_option(context, update)
                return
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=boolean_to_user(
                    context.chat_data["configuration"]["configuration"]["reputation"][
                        "filters"
                    ][filter.name.lower()]["enabled"]
                ),
                reply_to_message_id=update.message.message_id,
            )
            return
        elif len(args) == 3 and args[1] == "set":
            try:
                filter = Reputation[args[0].upper()]
            except KeyError:
                await self.invalid_option(context, update)
                return
            if args[2] == "enabled":
                context.chat_data["configuration"]["configuration"]["reputation"][
                    "filters"
                ][filter.name.lower()]["enabled"] = True
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.cli_success.value,
                    reply_to_message_id=update.message.message_id,
                )
                return
            elif args[2] == "disabled":
                context.chat_data["configuration"]["configuration"]["reputation"][
                    "filters"
                ][filter.name.lower()]["enabled"] = False
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.cli_success.value,
                    reply_to_message_id=update.message.message_id,
                )
                return
            else:
                await self.invalid_option(context, update)
                return
        elif len(args) > 2 and args[1] == "custom":
            try:
                filter = Reputation[args[0].upper()]
            except KeyError:
                await self.invalid_option(context, update)
                return
            await self.reputation_filter_handler(context, update, args[2:], filter)
            return
        else:
            await self.invalid_option(context, update)
            return

    async def int_handler(self, context=None, update=None, args=None, store=None):
        if store == CliStoreType.EXCHANGE:
            store_path = context.chat_data["configuration"]["configuration"]["coins"][
                "exchangeRate"
            ]
        elif store == CliStoreType.ODDS:
            store_path = context.chat_data["configuration"]["configuration"]["lottery"][
                "odds"
            ]
        elif store == CliStoreType.MULTIPLIER:
            store_path = context.chat_data["configuration"]["configuration"]["lottery"][
                "multiplier"
            ]
        elif store == CliStoreType.TRANSLATION:
            store_path = context.chat_data["configuration"]["configuration"][
                "translation"
            ]["cost"]
        if args[0] == "get":
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f"{store_path}",
                reply_to_message_id=update.message.message_id,
            )
            return
        elif args[0] == "set":
            if _is_type_int(args[1]) and _is_positive(args[1]):
                if store == CliStoreType.EXCHANGE:
                    context.chat_data["configuration"]["configuration"]["coins"][
                        "exchangeRate"
                    ] = int(args[1])
                elif store == CliStoreType.ODDS:
                    context.chat_data["configuration"]["configuration"]["lottery"][
                        "odds"
                    ] = int(args[1])
                elif store == CliStoreType.MULTIPLIER:
                    context.chat_data["configuration"]["configuration"]["lottery"][
                        "multiplier"
                    ] = int(args[1])
                elif store == CliStoreType.TRANSLATION:
                    context.chat_data["configuration"]["configuration"]["translation"][
                        "cost"
                    ] = int(args[1])
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=Messages.cli_success.value,
                    reply_to_message_id=update.message.message_id,
                )
                return
            else:
                await self.invalid_option(context, update)
                return
        else:
            await self.invalid_option(context, update)
            return

    async def execute(self, context=None, update=None, args=None):
        user_id = update.message.from_user.id
        if not await _get_user_type(update, context, user_id) in ChatMemberStatus.OWNER:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=Messages.unauthorized_admin.value,
                reply_to_message_id=update.message.message_id,
            )
            return
        if len(args) == 0 or args[0] == "help":
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=textwrap.dedent(self.help_text_main),
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return
        elif len(args) > 0:
            if args[0] == "coins":
                await self.coin_handler(context, update, args[1:])
                return
            elif args[0] == "lottery":
                await self.lottery_handler(context, update, args[1:])
                return
            elif args[0] in ("translation", "tts"):
                await self.translation_handler(context, update, args[1:])
                return
            elif args[0] == "filters":
                await self.filters_handler(context, update, args[1:])
                return
            elif args[0] == "reputation":
                await self.reputation_handler(context, update, args[1:])
                return
        else:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=textwrap.dedent(self.help_text_main),
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.HTML,
            )
            return


supported_commands = {
    itm[1]().__str__(): itm[1]()
    for itm in inspect.getmembers(sys.modules[__name__], predicate=_type_base_command)
}

del supported_commands["base"]
