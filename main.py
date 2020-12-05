#!/usr/bin/env python

import logging, random, json
from telegram.ext import CommandHandler, MessageHandler, Filters, DelayQueue, Updater, PicklePersistence
from telegram.error import (TelegramError, Unauthorized, BadRequest, 
                            TimedOut, ChatMigrated, NetworkError, RetryAfter)
import telegram.bot
from telegram.ext import messagequeue as mq
from telegram.utils.request import Request

import time
import functools

from random import randrange

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
# dqueue1 = DelayQueue(burst_limit=20, time_limit_ms=60000)

LEVELS = []
STATIC_CONFIGURATION = []

class MQBot(telegram.bot.Bot):
    '''A subclass of Bot which delegates send method handling to MQ'''
    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        '''Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments'''
        return super(MQBot, self).send_message(*args, **kwargs)

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
    try:
        messageString = update.message.text
    except AttributeError:
        return

    messageString = messageString.lower()

    chat_id = update.message.chat.id

    # print(context.bot.get_chat_member(chat_id, update.message.from_user.id))
    # print(context.chat_data)
    # print(update)
    epoch_time = int(time.time())

    if messageString == "!start":
        if context.chat_data:
            context.bot.send_message(chat_id=chat_id, text="You already ran the command. If you want to reset the settings run !reset")
        else:
            context.bot.send_message(chat_id=chat_id, text="We're ready! Type away.")
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
        context.bot.send_message(chat_id=chat_id, text="Data expunged!")

    elif (messageString == "!topxp" or messageString == "!toplvl") and context.chat_data:
        chat_text = "The current XP table: \n"
        users = context.chat_data['users']
        usersSort = sorted(users.items(),key=lambda x: x[1]['xp'], reverse=True)
        users = {}
        for itm in usersSort:
            users[itm[0]] = itm[1]
        for idx, user in enumerate(users):
            user_xp = users[user]["xp"]
            for idx2, lvl in enumerate(LEVELS):
                if user_xp < lvl:
                    chat_text += '{} <a href="tg://user?id={}">{} {}</a> ({}/{})\n'.format(idx + 1, users[user]["user_id"], users[user]["user_first"], users[user]["user_last"], users[user]["xp"], lvl)
                    break
                elif user_xp == lvl:
                    chat_text += '{} <a href="tg://user?id={}">{} {}</a> ({}/{})\n'.format(idx + 1, users[user]["user_id"], users[user]["user_first"], users[user]["user_last"], users[user]["xp"], LEVELS[idx2 + 1])
                    break
        context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")

    elif messageString == "!toprep":
        chat_text = "The current Reputation table: \n"
        users = context.chat_data['users']
        usersSort = sorted(users.items(),key=lambda x: x[1]['rep'], reverse=True)
        users = {}
        for itm in usersSort:
            users[itm[0]] = itm[1]
        for idx, user in enumerate(users):
            chat_text += '{} <a href="tg://user?id={}">{} {}</a> ({})\n'.format(idx + 1, users[user]["user_id"], users[user]["user_first"], users[user]["user_last"], users[user]["rep"])
        context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")

    elif messageString.startswith("!setxp"):
        message = messageString.split(" ")
        if len(message) != 2:
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        elif not representsInt(message[1]):
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        else:
            xp_set = int(message[1])
            if update.message.reply_to_message == None:
                context.bot.send_message(chat_id=chat_id, text="Please reply to a user's comment to change their XP!")
            else:
                requester_user_id = update.message.from_user.id
                requester_details = context.bot.get_chat_member(chat_id, requester_user_id)
                if requester_details.status == "creator":
                    changing_user_id = update.message.reply_to_message.from_user.id
                    changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
                    if not changing_user_data["user"]["is_bot"]:
                        chat_data = context.chat_data
                        chat_data["users"][changing_user_id]["xp"] = xp_set
                        context.bot.send_message(chat_id=chat_id, text="XP changed successfully.")
                else:
                    context.bot.send_message(chat_id=chat_id, text="Unauthorized user.")

    elif messageString.startswith("!setrep"):
        message = messageString.split(" ")
        if len(message) != 2:
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        elif not representsInt(message[1]):
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        else:
            rep_set = int(message[1])
            if update.message.reply_to_message == None:
                context.bot.send_message(chat_id=chat_id, text="Please reply to a user's comment to change their Reputation!")
            else:
                requester_user_id = update.message.from_user.id
                requester_details = context.bot.get_chat_member(chat_id, requester_user_id)
                if requester_details.status == "creator":
                    changing_user_id = update.message.reply_to_message.from_user.id
                    changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
                    if not changing_user_data["user"]["is_bot"]:
                        chat_data = context.chat_data
                        chat_data["users"][changing_user_id]["rep"] = rep_set
                        context.bot.send_message(chat_id=chat_id, text="Reputation changed successfully.")
                else:
                    context.bot.send_message(chat_id=chat_id, text="Unauthorized user.")
    
    elif messageString == "+":
        if update.message.reply_to_message != None:
            requester_user_id = update.message.from_user.id
            changing_user_id = update.message.reply_to_message.from_user.id
            changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
            if requester_user_id != changing_user_id and not changing_user_data['user']['is_bot']:
                requester = context.chat_data['users'][requester_user_id]
                changer = context.chat_data['users'][changing_user_id]
                chat_data = context.chat_data
                chat_data['users'][changing_user_id]['rep'] += 1
                context.chat_data.update(chat_data)
                bot_message = "<b>{} {}</b> ({}) has increased reputation of <b>{} {}</b> ({})".format(requester['user_first'], requester['user_last'], requester['rep'], changer['user_first'], changer['user_last'], changer['rep'])
                context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")

    elif messageString == "-":
        if update.message.reply_to_message != None:
            requester_user_id = update.message.from_user.id
            changing_user_id = update.message.reply_to_message.from_user.id
            changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
            if requester_user_id != changing_user_id and not changing_user_data['user']['is_bot']:
                requester = context.chat_data['users'][requester_user_id]
                changer = context.chat_data['users'][changing_user_id]
                chat_data = context.chat_data
                chat_data['users'][changing_user_id]['rep'] -= 1
                context.chat_data.update(chat_data)
                bot_message = "<b>{} {}</b> ({}) has decreased reputation of <b>{} {}</b> ({})".format(requester['user_first'], requester['user_last'], requester['rep'], changer['user_first'], changer['user_last'], changer['rep'])
                context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")
        
    elif messageString == "!debug" and context.chat_data:
        context.bot.send_message(chat_id=chat_id, text=json.dumps(context.chat_data["users"]))

    elif messageString == "!about":
        context.bot.send_message(chat_id=chat_id, text="Hello. I'm an XP and Reputation Bot developed by Nischay-Pro. Inspired by Combot.")

    elif messageString == "!getxp":
        requester_user_id = update.message.from_user.id
        requester = context.chat_data['users'][requester_user_id]
        bot_message = "<b>{} {}</b> you have {} xp.".format(requester['user_first'], requester['user_last'], requester['xp'])
        context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML", quote=True)

    elif messageString == "!getrep":
        requester_user_id = update.message.from_user.id
        requester = context.chat_data['users'][requester_user_id]
        bot_message = "<b>{} {}</b> you have {} reputation.".format(requester['user_first'], requester['user_last'], requester['rep'])
        context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML", quote=True)

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
                            old_xp = chat_data["users"][user_id]["xp"]
                            old_level = findLevel(old_xp)
                            multiplier = 1
                            if STATIC_CONFIGURATION[0]["lottery"]["enabled"]:
                                if 1 == randrange(1, STATIC_CONFIGURATION[0]["lottery"]["odds"] + 1):
                                    multiplier = STATIC_CONFIGURATION[0]["lottery"]["multiplier"]
                            gained_xp = round(randrange(1, 12) * multiplier)
                            if multiplier != 1:
                                context.bot.send_message(chat_id=chat_id, text="7️⃣7️⃣7️⃣ Lucky message! {} has received {} XP!".format(update.message.from_user.first_name, gained_xp))
                            chat_data["users"][user_id]["xp"] += gained_xp
                            new_xp = chat_data["users"][user_id]["xp"]
                            new_level = findLevel(new_xp)
                            chat_data["users"][user_id]["last_message"] = epoch_time
                            delta_award_time = randrange(1 * 60, 4 * 60)
                            chat_data["users"][user_id]["delta_award_time"] = delta_award_time
                            context.chat_data.update(chat_data)
                            if old_level != new_level and old_level[0] != 0:
                                context.bot.send_message(chat_id=chat_id, text="🌟 {} has reached level {}!".format(update.message.from_user.first_name, old_level[0]))

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def findLevel(xp):
    for idx, itm in enumerate(LEVELS):
        if xp <= itm:
            return (idx, itm)

def representsInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False

@functools.lru_cache(maxsize=500)
def genLevel(x):
    if x == 0:
        return x
    elif x == 1:
        return 100

    if x % 2 == 0:
        xp = 2 * genLevel(x - 1) - genLevel(x - 2) + 35
    else:
        xp = 2 * genLevel(x - 1) - genLevel(x - 2) + 135

    return xp

def main():
    """Start the bot."""
    config = json.loads(open("config.json").read())
    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    request = Request(con_pool_size=8)
    if not config["bot_token"] == "<your token here>":
        STATIC_CONFIGURATION.append(config)
        for i in range(501):
            LEVELS.append(genLevel(i))
        data_persistence = PicklePersistence(filename="db")
        bot = MQBot(config["bot_token"], request=request, mqueue=q)
        updater = Updater(bot=bot, persistence=data_persistence, use_context=True)
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