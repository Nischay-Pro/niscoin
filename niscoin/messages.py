from enum import Enum


class Messages(Enum):
    def __str__(self):
        return str(self.value)

    unauthorized_user = "You are not authorized to use this command."
    unauthorized_admin = "Only the owner can use this command."
    self_not_allowed = "You can't use this command on yourself."
    initate_success = "Niscoin has been initiated. Type away!"
    initate_fail = "Niscoin has already been initiated."

    coins_disabled = "Coins is disabled for this chat."
    rep_disabled = "Reputation is disabled for this chat."

    set_coins_invalid = "Please specify a valid number of coins."
    set_coins_noreply = "Please reply to the user you want to set coins for."
    set_coins_success = "Coins set successfully."

    set_xp_invalid = "Please specify a valid number of XP."
    set_xp_noreply = "Please reply to the user you want to set XP for."
    set_xp_success = "XP set successfully."

    set_rep_invalid = "Please specify a valid number of reputation."
    set_rep_noreply = "Please reply to the user you want to set reputation for."
    set_rep_success = "Reputation set successfully."

    exchange_invalid = "Please specify a valid coin amount to exchange your XP for."
    exchange_success = "Successfully exchanged coins."
    exchange_cost = "The exchange cost is {cost} XP."
    exchange_not_enough = "You don't have enough XP to exchange."

    give_noreply = "Please reply to the user you want to give coins to."
    give_invalid = "Please specify a valid amount of coins to give."
    give_success = "Successfully gave {amount} coins to {user}."
    give_insufficient = "You don't have enough coins to give."

    get_coins = "You have {coins} coins."
    get_xp = "You have {xp} XP with {level} levels."
    get_reputation = "You have {reputation} reputation."

    translation_disabled = "Text To Speech (TTS) is disabled for this chat."
    translation_not_enough_coins = "You don't have enough coins for TTS."
    translation_no_message = "Please type the message you want to TTS or reply to the message you want to TTS."
    translation_max_length = "The maximum length of a TTS message is 1000 characters."
    translation_invalid_slow_mode = "Please specify a valid flag for slow mode."
    translation_invalid_language = "Please specify a valid language."
    translation_cost = "The translation cost is {cost} coins."

    reputation_positive = "<b>{user_give} ({user_give_rep})</b> increased the reputation of <b>{user_receive} ({user_receive_rep})</b>."
    reputation_negative = "<b>{user_give} ({user_give_rep})</b> decreased the reputation of <b>{user_receive} ({user_receive_rep})</b>."
    reputation_unauthorized = (
        "Only the owner and the administrators can use this command."
    )

    cli_success = "Parameter changed successfully."
    cli_invalid = "Invalid cli arguments."
    cli_filter_word_exists = "The filter word {word} already exists."
    cli_filter_word_does_not_exist = "The filter word {word} does not exist."
    cli_filter_word_invalid_characters = (
        "The filter word {word} contains invalid characters."
    )
    cli_filter_word_added = "The filter word {word} has been added."
    cli_filter_word_removed = "The filter word {word} has been removed."
    cli_user_already_ignored = "User {user} is already ignored."
    cli_user_does_not_exist = "User with ID {user} does not exist."
    cli_user_added = "User {user} has been added to the ignore list."
    cli_user_removed = "User {user} has been removed from the ignore list."
    cli_user_not_in_ignore_list = "User {user} is not in the ignore list."
    cli_ignore_list_empty = "No users are currently ignored."
