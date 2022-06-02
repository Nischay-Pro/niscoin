import textwrap
from telegram import (
    InlineKeyboardButton,
)


def get_help_keyboard() -> list:
    return list(
        map(
            list,
            zip(
                *[
                    iter(
                        [
                            InlineKeyboardButton(
                                f"{itm.keyboard_text}", callback_data=itm.name
                            )
                            for itm in iter(help_strings.values())
                        ]
                    )
                ]
                * 3
            ),
        )
    )


def get_back_keyboard() -> list:
    return [[InlineKeyboardButton("Back", callback_data="back")]]


class HelpString:
    def __init__(self, name, description, keyboard_text, command):
        self.name = name
        self.description = textwrap.dedent(description)
        self.keyboard_text = keyboard_text
        self.command = command

    def __str__(self):
        return self.description


help_strings = {
    "start": HelpString(
        "start",
        """
        Start the bot\. You can run this command only in the group chat\.
        Invoke the command by typing `\!start` in the group chat\.

        *Who can run this command?*
        → Group Owner
        """,
        "Start",
        "\!start",
    ),
    "reset": HelpString(
        "reset",
        """
        Reset the bot to default settings *\(Wipes bot data\!\)*\.
        
        *Who can run this command?*
        → Group Owner
        """,
        "Reset",
        "\!reset",
    ),
    "topxp": HelpString(
        "topxp",
        """
        Display a table containing users with the most XP and level they current are\.
        Only the top 10 users are displayed\.
        
        *Who can run this command?*
        → Anyone
        """,
        "Top XP",
        "\!topxp",
    ),
    "toplvl": HelpString(
        "toplvl",
        """
        Alias to topxp\.

        *Who can run this command?*
        → Anyone
        """,
        "Top XP",
        "\!toplvl",
    ),
    "topcoins": HelpString(
        "topcoins",
        """
        Display a table containing users with the highest number of coins\.
        Only the top 10 users are displayed\.
        
        *Who can run this command?*
        → Anyone
        """,
        "Top Coins",
        "\!topcoins",
    ),
    "toprep": HelpString(
        "toprep",
        """
        Display a table containing users with the highest reputation\.
        Only the top 10 users are displayed\.

        *Who can run this command?*
        → Anyone
        """,
        "Top Reputation",
        "\!toprep",
    ),
    "setxp": HelpString(
        "setxp",
        """
        Sets the XP of a user\. You need to reply to the user you want to set XP for\.

        *Who can run this command?*
        → Group Owner
        → Admins
        """,
        "Set XP",
        "\!setxp",
    ),
    "setrep": HelpString(
        "setrep",
        """
        Sets the reputation of a user\. You need to reply to the user you want to set rep for\.

        *Who can run this command?*
        → Group Owner
        → Admins
        """,
        "Set Reputation",
        "\!setrep",
    ),
    "setcoins": HelpString(
        "setcoins",
        """
        Sets the coins of a user\. You need to reply to the user you want to set coins for\.

        *Who can run this command?*
        → Group Owner
        → Admins
        """,
        "Set Coins",
        "\!setcoins",
    ),
    "exchange": HelpString(
        "exchange",
        """
        Exchange XP for coins\.
        
        *Example usage*: 
        `\!exchange 10`

        This will exchange 10 XP for 1 coin\. You can also configure 
        the exchange rate in the settings using the `\!cli` command\.

        *Who can run this command?*
        → Anyone
        """,
        "Exchange",
        "\!exchange",
    ),
    "getcoins": HelpString(
        "getcoins",
        """
        Gets the number of coins \(Self\)\.

        *Who can run this command?*
        → Anyone
        """,
        "Get Coins",
        "\!getcoins",
    ),
    "play": HelpString(
        "play",
        """
        Spend coins to TTS a custom provided message\.

        *Example usage*:
        WIP

        This will play the provided message in exchange for coins\.
        You can also configure the cost of the message in the settings
        using the `\!cli` command\.

        *Who can run this command?*
        → Anyone
        """,
        "Play",
        "\!play",
    ),
    "give": HelpString(
        "give",
        """
        Give coins to a user\. You need to reply to the user you want to give coins to\.

        *Example usage*:
        `\!give 10`

        This will give 10 coins to the user you replied to\.

        *Who can run this command?*
        → Anyone
        """,
        "Give",
        "\!give",
    ),
    "debug": HelpString(
        "debug",
        """
        Access bot debug info \(Restricted\)\.

        *Who can run this command?*
        → Group Owner
        """,
        "Debug",
        "\!debug",
    ),
    "about": HelpString(
        "about",
        """
        Display the about information for this bot\.
        
        *Who can run this command?*
        → Anyone
        """,
        "About",
        "\!about",
    ),
    "getxp": HelpString(
        "getxp",
        """
        Get the current XP and level of a user \(Self\)\.

        *Example usage*:
        `\!getxp`

        *Who can run this command?*
        → Anyone
        """,
        "Get XP",
        "\!getxp",
    ),
    "getlvl": HelpString(
        "getlvl",
        """
        Alias to getxp\.

        *Who can run this command?*
        → Anyone
        """,
        "Get XP",
        "\!getlvl",
    ),
    "getrep": HelpString(
        "getrep",
        """
        Get the current reputation of a user \(Self\)\.

        *Example usage*:
        `\!getrep`

        *Who can run this command?*
        → Anyone
        """,
        "Get Reputation",
        "\!getrep",
    ),
    "getfilters": HelpString(
        "getfilters",
        """
        Get the list of reputation filter words\.

        *Who can run this command?*
        → Anyone
        """,
        "Get Filters",
        "\!getfilters",
    ),
    "statistics": HelpString(
        "statistics",
        """
        Displays the general statistics of Niscoin\.
        
        *Who can run this command?*
        → Anyone
        """,
        "Statistics",
        "\!statistics",
    ),
}
