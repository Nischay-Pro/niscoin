#!/usr/bin/env python

import logging, random, json
from telegram.ext import CommandHandler, MessageHandler, Filters, DelayQueue, Updater, PicklePersistence
from telegram.error import (TelegramError, Unauthorized, BadRequest, 
                            TimedOut, ChatMigrated, NetworkError, RetryAfter)
import telegram.bot
from telegram.utils.request import Request

import time

from random import randrange

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
# dqueue1 = DelayQueue(burst_limit=20, time_limit_ms=60000)

def error_callback(update, context):
    try:
        raise context.error
    except Unauthorized:
        print(update)
    except BadRequest:
        print("# handle malformed requests - read more below!")
    except TimedOut:
        print("# handle slow connection problems")
    except NetworkError:
        print("# handle other connection problems")
    except RetryAfter:
        print("Rate Limited")
    except TelegramError:
        print("Telegram Error happened")

def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(update, context):
    """Echo the user message."""
    messageString = update.message.text.lower()

    chat_id = update.message.chat.id

    print(context.chat_data)
    epoch_time = int(time.time())

    if messageString == "!start":
        if context.chat_data:
            context.bot.send_message(chat_id=chat_id, text="We are already tracking your chat! Use !reset to reset this chat settings.")
        else:
            context.bot.send_message(chat_id=chat_id, text="Hello! You can start typing now and we'll be tracking your chats.")
            user_id = update.message.from_user.id
            user_first = update.message.from_user.first_name
            user_last = update.message.from_user.last_name
            if user_last == None:
                user_last = ""
            users = {user_id: {"user_id": user_id, "user_first": user_first, "user_last": user_last, "xp": 0, "rep": 0, "last_message": 0, "delta_award_time": 0}}
            chat_data = {"init" : True, "users": users}
            context.chat_data.update(chat_data)

    elif messageString == "!reset":
        user_id = update.message.from_user.id
        user_first = update.message.from_user.first_name
        user_last = update.message.from_user.last_name
        if user_last == None:
            user_last = ""
        users = {user_id: {"user_id": user_id, "user_first": user_first, "user_last": user_last, "xp": 0, "rep": 0, "last_message": 0, "delta_award_time": 0}}
        chat_data = {"init" : True, "users": users}
        context.chat_data.update(chat_data)
        context.bot.send_message(chat_id=chat_id, text="Chat Settings successfully purged!")

    elif messageString == "!topxp" and context.chat_data:
        chat_text = "The current XP table \n"
        users = context.chat_data['users']
        sorted(users.items(),key=lambda x: x[1]['xp'],reverse=True)
        for idx, user in enumerate(users):
            chat_text += "{}\t{} {}\t{}\n".format(idx + 1, users[user]["user_first"], users[user]["user_last"], users[user]["xp"])
            
        context.bot.send_message(chat_id=chat_id, text=chat_text)

    else:
        if context.chat_data and "init" in context.chat_data:
            if context.chat_data.get("init"):
                user_id = update.message.from_user.id
                if not user_id in context.chat_data["users"]:
                    user_first = update.message.from_user.first_name
                    user_last = update.message.from_user.last_name
                    if user_last == None:
                        user_last = ""
                    users = context.chat_data["users"]
                    users.update({user_id: {"user_id": user_id, "user_first": user_first, "user_last": user_last, "xp": 0, "rep": 0, "last_message": epoch_time, "delta_award_time" : 0}})
                    context.chat_data["users"].update(users)
                else:
                    last_message_time = context.chat_data["users"][user_id]["last_message"]
                    if last_message_time == 0:
                        chat_data = context.chat_data
                        chat_data["users"][user_id]["xp"] += randrange(1, 12)
                        chat_data["users"][user_id]["last_message"] = epoch_time
                        delta_award_time = randrange(1 * 60, 4 * 60)
                        chat_data["users"][user_id]["delta_award_time"] = delta_award_time
                        context.chat_data.update(chat_data)
                    else:
                        chat_data = context.chat_data
                        delta_award_time = chat_data["users"][user_id]["delta_award_time"]
                        if epoch_time - last_message_time >= delta_award_time:
                            chat_data["users"][user_id]["xp"] += randrange(1, 12)
                            chat_data["users"][user_id]["last_message"] = epoch_time
                            delta_award_time = randrange(1 * 60, 4 * 60)
                            chat_data["users"][user_id]["delta_award_time"] = delta_award_time
                            context.chat_data.update(chat_data)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    config = json.loads(open("config.json").read())
    if not config["bot_token"] == "<your token here>":
        data_persistence = PicklePersistence(filename="db")
        updater = Updater(config["bot_token"], persistence=data_persistence, use_context=True)
    else:
        print("Missing Bot Token")
        exit()

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # error handler
    dp.add_error_handler(error_callback)

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()