import functools
from typing import Any
from telegram import Update
from bisect import bisect_left
from re import match


@functools.lru_cache(maxsize=500)
def genLevels(x):
    if x == 0:
        return x
    elif x == 1:
        return 100

    if x % 2 == 0:
        xp = 2 * genLevels(x - 1) - genLevels(x - 2) + 35
    else:
        xp = 2 * genLevels(x - 1) - genLevels(x - 2) + 135

    return xp


def get_level_from_xp(xp: int, levels: list) -> int:
    return bisect_left(levels, xp)


async def configure_levels(update: Update, context: Any) -> None:
    if "configuration" in context.bot_data.keys():
        try:
            levels = context.bot_data["configuration"]["levels"]
        except KeyError:
            levels = [genLevels(i) for i in range(1, 501)]
            context.bot_data["configuration"]["levels"] = levels
    else:
        levels = [genLevels(i) for i in range(1, 501)]
        context.bot_data["configuration"] = {"levels": levels}


def booleanify(value: str) -> bool:
    if value.lower() in ["true", "yes", "on", "1"]:
        return True
    elif value.lower() in ["false", "no", "off", "0"]:
        return False
    else:
        raise ValueError


def boolean_to_user(value: bool) -> str:
    if value:
        return "Enabled"
    else:
        return "Disabled"


def match_only_alphanumeric(value: str) -> bool:
    return match(r"^[a-zA-Z0-9]+$", value) is not None
