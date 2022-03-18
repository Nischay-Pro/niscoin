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
import gtts
from multiprocessing import Pool

import subprocess
import pickle

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
    chat_id = update.message.chat.id
    chat_text = "Commands available are: \n"
    helpStrings = STATIC_CONFIGURATION[1]["commands"]
    for itm in helpStrings.keys():
        chat_text += '<b>!{}</b> → {}\n'.format(itm, helpStrings[itm])
    context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")


def echo(update, context):
    """Echo the user message."""
    try:
        messageString = update.message.text
    except AttributeError:
        return

    translate_options = gtts.lang.tts_langs().keys()

    messageString = messageString.lower()

    chat_id = update.message.chat.id

    epoch_time = int(time.time())

    reputation_awards = ("🥇", "🥈", "🥉")

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
            users = {user_id: {"user_id": user_id, "user_first": user_first, "user_last": user_last, "xp": 0, "rep": 0, "last_message": 0, "delta_award_time": 0, "coins": 0}}
            chat_data = {"init" : True, "users": users, "duels": {}}
            context.chat_data.update(chat_data)

    elif messageString == "!reset":
        user_id = update.message.from_user.id
        user_first = update.message.from_user.first_name
        user_last = update.message.from_user.last_name
        requester_details = context.bot.get_chat_member(chat_id, user_id)
        if requester_details.status == "creator":
            if user_last == None:
                user_last = ""
            users = {user_id: {"user_id": user_id, "user_first": user_first, "user_last": user_last, "xp": 0, "rep": 0, "last_message": 0, "delta_award_time": 0, "coins": 0}}
            chat_data = {"init" : True, "users": users, "duels": {}}
            context.chat_data.update(chat_data)
            context.bot.send_message(chat_id=chat_id, text="Data expunged!")
        else:
            context.bot.send_message(chat_id=chat_id, text="Unauthorized user.")

    elif (messageString == "!topxp" or messageString == "!toplvl") and context.chat_data:
        chat_text = "The current XP table: \n"
        users = context.chat_data['users']
        usersSort = sorted(users.items(),key=lambda x: x[1]['xp'], reverse=True)
        users = {}
        for itm in usersSort:
            users[itm[0]] = itm[1]
        for idx, user in enumerate(tuple(users.keys())[0:10]):
            award = ""
            if idx == 0:
                award = "🥇"
            elif idx == 1:
                award = "🥈"
            elif idx == 2:
                award = "🥉"
            user_xp = users[user]["xp"]
            for idx2, lvl in enumerate(LEVELS):
                if user_xp < lvl:
                    chat_text += '{} <a href="tg://user?id={}">{} {}</a> ({}/{}) - Level {} {}\n'.format(idx + 1, users[user]["user_id"], users[user]["user_first"], users[user]["user_last"], users[user]["xp"], lvl, idx2, award)
                    break
                elif user_xp == lvl:
                    chat_text += '{} <a href="tg://user?id={}">{} {}</a> ({}/{}) - Level {} {}\n'.format(idx + 1, users[user]["user_id"], users[user]["user_first"], users[user]["user_last"], users[user]["xp"], LEVELS[idx2 + 1], idx2, award)
                    break
        context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")

    elif messageString == "!topcoins" and context.chat_data:
        chat_text = "The current Coins table: \n"
        users = context.chat_data['users']
        usersSort = sorted(users.items(),key=lambda x: x[1]['coins'], reverse=True)
        users = {}
        for itm in usersSort:
            users[itm[0]] = itm[1]
        for idx, user in enumerate(tuple(users.keys())[0:10]):
            try:
                chat_text += '{} <a href="tg://user?id={}">{} {}</a> ({})\n'.format(idx + 1, users[user]["user_id"], users[user]["user_first"], users[user]["user_last"], users[user]["coins"])
            except KeyError:
                pass
        context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")

    elif messageString == "!toprep":
        chat_text = "The current Reputation table: \n"
        users = context.chat_data['users']
        usersSort = sorted(users.items(),key=lambda x: x[1]['rep'], reverse=True)
        users = {}
        for itm in usersSort:
            users[itm[0]] = itm[1]
        for idx, user in enumerate(tuple(users.keys())[0:10]):
            award = ""
            if idx == 0:
                award = "🥇"
            elif idx == 1:
                award = "🥈"
            elif idx == 2:
                award = "🥉"
            chat_text += '{} <a href="tg://user?id={}">{} {}</a> ({}){}\n'.format(idx + 1, users[user]["user_id"], users[user]["user_first"], users[user]["user_last"], users[user]["rep"], award)
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

    elif messageString.startswith("!setcoins"):
        message = messageString.split(" ")
        if len(message) != 2:
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        elif not representsInt(message[1]):
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        else:
            coins_set = int(message[1])
            if update.message.reply_to_message == None:
                context.bot.send_message(chat_id=chat_id, text="Please reply to a user's comment to change their coins!")
            else:
                requester_user_id = update.message.from_user.id
                requester_details = context.bot.get_chat_member(chat_id, requester_user_id)
                if requester_details.status == "creator":
                    changing_user_id = update.message.reply_to_message.from_user.id
                    changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
                    if not changing_user_data["user"]["is_bot"]:
                        chat_data = context.chat_data
                        try:
                            chat_data['users'][changing_user_id]['coins'] = coins_set
                        except KeyError:
                            chat_data['users'][changing_user_id].update({"coins": coins_set})
                        context.chat_data.update(chat_data)
                        context.bot.send_message(chat_id=chat_id, text="Coins changed successfully.")
                else:
                    context.bot.send_message(chat_id=chat_id, text="Unauthorized user.")

    elif messageString in STATIC_CONFIGURATION[0]["reputation"]["minipositive"]:
        if update.message.reply_to_message != None:
            changeReputation(update, context, chat_id, True, 0.5, STATIC_CONFIGURATION, reputation_awards)
    
    elif messageString in STATIC_CONFIGURATION[0]["reputation"]["positive"]:
        if update.message.reply_to_message != None:
            changeReputation(update, context, chat_id, True, 1, STATIC_CONFIGURATION, reputation_awards)

    elif messageString in STATIC_CONFIGURATION[0]["reputation"]["megapositive"]:
        if update.message.reply_to_message != None:
            changeReputation(update, context, chat_id, True, 2, STATIC_CONFIGURATION, reputation_awards)

    elif messageString in STATIC_CONFIGURATION[0]["reputation"]["mininegative"]:
        if update.message.reply_to_message != None:
            changeReputation(update, context, chat_id, False, 0.5, STATIC_CONFIGURATION, reputation_awards)

    elif messageString in STATIC_CONFIGURATION[0]["reputation"]["negative"]:
        if update.message.reply_to_message != None:
            changeReputation(update, context, chat_id, False, 1, STATIC_CONFIGURATION, reputation_awards)

    elif messageString in STATIC_CONFIGURATION[0]["reputation"]["meganegative"]:
        if update.message.reply_to_message != None:
            changeReputation(update, context, chat_id, False, 2, STATIC_CONFIGURATION, reputation_awards)

    elif messageString.startswith("!exchange"):
        message = messageString.split(" ")
        if message[0] == "!exchange" and len(message) == 1:
            context.bot.send_message(chat_id=chat_id, text="Exchange your XP for coins. Rate 10 XP = 1 coins.")
        elif len(message) == 2 and representsInt(message[1]):
            coins_purchase = int(message[1])
            if coins_purchase > 0:
                requester_user_id = update.message.from_user.id
                requester = context.chat_data['users'][requester_user_id]
                requester_xp = requester['xp']
                if requester_xp >= coins_purchase * 10:
                    chat_data = context.chat_data
                    chat_data['users'][requester_user_id]['xp'] -= coins_purchase * 10
                    try:
                        chat_data['users'][requester_user_id]['coins'] += coins_purchase
                    except KeyError:
                        chat_data['users'][requester_user_id].update({"coins": coins_purchase})
                    context.chat_data.update(chat_data)
                    context.bot.send_message(chat_id=chat_id, text="Transaction Complete.")
                else:
                    context.bot.send_message(chat_id=chat_id, text="Insufficient funds.")
            else:
                context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        else:
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")

    elif messageString == "!getcoins":
        requester_user_id = update.message.from_user.id
        requester = context.chat_data['users'][requester_user_id]
        try:
            coins_avail = requester['coins']
        except KeyError:
            coins_avail = 0
        bot_message = "<b>{} {}</b> you have {} coin(s).".format(requester['user_first'], requester['user_last'], coins_avail)
        context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")

    elif messageString.startswith("!play"):
        if '"' in messageString:
            temp = messageString.split('"')
            command = temp[0].split(" ")
            tts_string = temp[1]
            command.pop(-1)
            message = command
            message.append(tts_string)
        else:
            message = messageString.split(" ")
        if len(message) == 1 and messageString == "!play":
            context.bot.send_message(chat_id=chat_id, text="TTS any string at 50 coins per translation! \n Format !play <language code> <fast mode> <tts string>")
        elif len(message) == 2 and messageString == "!play lang":
            language_support = gtts.lang.tts_langs()
            message = "The current languages supported are: \nCode | Language \n"
            for itm in language_support.keys():
                message += "{} : {}\n".format(itm, language_support[itm])
            context.bot.send_message(chat_id=chat_id, text=message)
        elif len(message) != 4:
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        else:
            if representsInt(message[2]) and message[1] in translate_options:
                slow = False
                if int(message[2]) == 0:
                    slow = True
                translate_text = str(message[3])
                if len(translate_text) > 1000:
                    context.bot.send_message(chat_id=chat_id, text="Translate Text limit reached maximum (1000).")
                    return
                requester_user_id = update.message.from_user.id
                requester = context.chat_data['users'][requester_user_id]
                lang = message[1]
                try:
                    requester_coins = context.chat_data["users"][requester_user_id]["coins"]
                except KeyError:
                    requester_coins = 0
                if requester_coins < 50:
                    context.bot.send_message(chat_id=chat_id, text="Insufficient funds!")
                else:
                    command_string = 'gtts-cli "{}" --lang {} --output hello.mp3'.format(translate_text, lang)
                    if slow:
                        command_string = 'gtts-cli "{}" --lang {} --output hello.mp3 --slow'.format(translate_text, lang)
                    try:
                        output = subprocess.check_output(command_string, stderr=subprocess.STDOUT, timeout=10, shell=True)
                        chat_data = context.chat_data
                        chat_data['users'][requester_user_id]['coins'] -= 50
                        context.chat_data.update(chat_data)
                        context.bot.send_voice(chat_id=chat_id, voice=open("hello.mp3", "rb"))
                    except subprocess.TimeoutExpired:
                        context.bot.send_message(chat_id=chat_id, text="Server Timed out!")
                    except:
                        context.bot.send_message(chat_id=chat_id, text="Critical Error!")
            else:
                context.bot.send_message(chat_id=chat_id, text="Invalid Command!")


    elif messageString.startswith("!give"):
        message = messageString.split(" ")
        if len(message) != 2:
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        elif not representsInt(message[1]):
            context.bot.send_message(chat_id=chat_id, text="Invalid Command!")
        else:
            coin_give = int(message[1])
            if coin_give > 0:
                if update.message.reply_to_message == None:
                    context.bot.send_message(chat_id=chat_id, text="Please reply to a user's comment to give them coins!")
                else:
                    requester_user_id = update.message.from_user.id
                    requester_details = context.bot.get_chat_member(chat_id, requester_user_id)
                    changing_user_id = update.message.reply_to_message.from_user.id
                    changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
                    if not changing_user_data["user"]["is_bot"] and requester_user_id != changing_user_id:
                        try:
                            requester_coins = context.chat_data["users"][requester_user_id]["coins"]
                        except KeyError:
                            requester_coins = 0
                        try:
                            changer_coins = context.chat_data["users"][changing_user_id]["coins"] 
                        except KeyError:
                            changer_coins = 0
                        if requester_coins >= coin_give:
                            chat_data = context.chat_data
                            chat_data["users"][requester_user_id]["coins"] -= coin_give
                            try:
                                chat_data["users"][changing_user_id]["coins"] += coin_give
                            except KeyError:
                                chat_data["users"][changing_user_id].update({"coins": coin_give})
                            context.chat_data.update(chat_data)
                            context.bot.send_message(chat_id=chat_id, text="Successfully given coins.")
                        else:
                            context.bot.send_message(chat_id=chat_id, text="Not enough coins.")
            else:
                context.bot.send_message(chat_id=chat_id, text="You have to give atleast 1 coin.")
        
    elif messageString == "!debug" and context.chat_data:
        requester_user_id = update.message.from_user.id
        requester_details = context.bot.get_chat_member(chat_id, requester_user_id)
        if requester_details.status == "creator":
            context.bot.send_message(chat_id=chat_id, text=json.dumps(context.chat_data["users"]))

    elif messageString == "!getfilters":
        chat_text = "Filters available are: \n"
        chat_text += "Reputation Increment → \n"
        helpStrings = STATIC_CONFIGURATION[0]["reputation"]["positive"]
        for itm in helpStrings:
            chat_text += '<b>{}</b>\n'.format(itm)
        chat_text += "Reputation Decrement → \n"
        helpStrings = STATIC_CONFIGURATION[0]["reputation"]["negative"]
        for itm in helpStrings:
            chat_text += '<b>{}</b>\n'.format(itm)
        context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")

    elif messageString == "!about":
        context.bot.send_message(chat_id=chat_id, text="Hello. I'm a bot developed by Nischay-Pro. You can find my code <a href='https://github.com/Nischay-Pro/python-telegram-xp'>here</a>. Inspired by Combot.", parse_mode="HTML")

    elif messageString == "!getxp" or messageString == "!getlvl":
        if update.message.reply_to_message == None:
            requester_user_id = update.message.from_user.id
            requester = context.chat_data['users'][requester_user_id]
            bot_message = "<b>{} {}</b> you have {} xp.".format(requester['user_first'], requester['user_last'], requester['xp'])
            context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")
        else:
            changing_user_id = update.message.reply_to_message.from_user.id
            changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
            if not changing_user_data['user']['is_bot']:
                changer = context.chat_data['users'][changing_user_id]
                bot_message = "<b>{} {}</b> has {} xp.".format(changer['user_first'], changer['user_last'], changer['xp'])
                context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")

    elif messageString == "!getrep":
        if update.message.reply_to_message == None:
            requester_user_id = update.message.from_user.id
            requester = context.chat_data['users'][requester_user_id]
            bot_message = "<b>{} {}</b> you have {} reputation.".format(requester['user_first'], requester['user_last'], requester['rep'])
            context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")
        else:
            changing_user_id = update.message.reply_to_message.from_user.id
            changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
            if not changing_user_data['user']['is_bot']:
                changer = context.chat_data['users'][changing_user_id]
                bot_message = "<b>{} {}</b> has {} reputation.".format(changer['user_first'], changer['user_last'], changer['rep'])
                context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")

    elif messageString == "!help":
        chat_text = "Commands available are: \n"
        helpStrings = STATIC_CONFIGURATION[1]["commands"]
        for itm in helpStrings.keys():
            chat_text += '<b>!{}</b> → {}\n'.format(itm, helpStrings[itm])
        context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")

    elif messageString == "!statistics":
        with open("db", "rb") as file:
            data = pickle.load(file)
        groups_count = len(data["chat_data"])
        users_count = len(data["user_data"])
        chat_text = "Currently Niscoin is serving {} groups with {} unique users.".format(groups_count, users_count)
        context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="HTML")

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
                    users.update({user_id: {"user_id": user_id, "user_first": user_first, "user_last": user_last, "xp": 0, "rep": 0, "last_message": epoch_time, "delta_award_time" : 0, "coins": 0}})
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

def translateWorker(*args):
    text = args[0][0]
    lang = args[0][1]
    slow = args[0][2]
    tts = gtts.gTTS(text, lang=lang, slow=slow)
    with open('hello.mp3', 'wb') as f:
        tts.write_to_fp(f)
    return True

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

def getAward(user, users_list, award_list):
    try:
        user_idx = users_list.index(user)
        return award_list[user_idx]
    except ValueError:
        return ""

def changeReputation(update, context, chat_id, positive, modifier, STATIC_CONFIGURATION, reputation_awards):
    requester_user_id = update.message.from_user.id
    changing_user_id = update.message.reply_to_message.from_user.id
    changing_user_data = context.bot.get_chat_member(chat_id, changing_user_id)
    if requester_user_id != changing_user_id and not changing_user_data['user']['is_bot']:
        users = context.chat_data['users']
        usersSort = sorted(users.items(),key=lambda x: x[1]['rep'], reverse=True)[0:3]
        usersSort = [user[0] for user in usersSort]
        requester = context.chat_data['users'][requester_user_id]
        changer = context.chat_data['users'][changing_user_id]
        chat_data = context.chat_data
        requester_award = getAward(requester_user_id, usersSort, reputation_awards)
        changer_award = getAward(changing_user_id, usersSort, reputation_awards)
        if requester_user_id not in STATIC_CONFIGURATION[0]["reputation"]["ignorelist"]:
            if positive:
                chat_data['users'][changing_user_id]['rep'] += modifier
                if modifier == 2:
                    chat_data['users'][requester_user_id]['rep'] -= 1
            else:
                chat_data['users'][changing_user_id]['rep'] -= modifier
                if modifier == 2:
                    chat_data['users'][requester_user_id]['rep'] -= 1
        context.chat_data.update(chat_data)
        if positive:
            type_message = "increased"
        else:
            type_message = "decreased"
        bot_message = "<b>{} {}</b> ({}) {} has {} reputation of <b>{} {}</b> ({}) {}".format(requester['user_first'], requester['user_last'], requester['rep'], requester_award, type_message, changer['user_first'], changer['user_last'], changer['rep'], changer_award)
        context.bot.send_message(chat_id=chat_id, text=bot_message, parse_mode="HTML")

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
    helpconfig = json.loads(open("help.json").read())
    q = mq.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
    request = Request(con_pool_size=8)
    if not config["bot_token"] == "<your token here>":
        STATIC_CONFIGURATION.append(config) 
        STATIC_CONFIGURATION.append(helpconfig)
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
