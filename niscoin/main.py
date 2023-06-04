#!/usr/bin/env python
import argparse
import os
import logging

try:
    import ujson as json
except ImportError:
    import json

from configuration import Configuration, PersistenceType
import conversation
from misc import configure_levels

try:
    import psycopg
except ImportError:
    pass
import sys
from logging.handlers import TimedRotatingFileHandler

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

try:
    from telegres import PostgresPersistence
except ImportError:
    pass

cwd = os.getcwd()
log_path = os.path.join(cwd, "logs")


def main():
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser(
        description="Command-line arguments to start niscoin."
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to config file.",
        required=False,
        default="config.json",
    )
    parser.add_argument(
        "--database",
        "-d",
        help="Path to database directory.",
        required=False,
        default="data",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.config):
        logger.error("[-] Config file not found.")
        exit(1)

    try:
        config_data = Configuration(json.load(open(args.config)))
    except json.decoder.JSONDecodeError as e:
        logger.error("[-] Could not read config file.")
        logger.error(f"[-] Error: {e}")
        exit(1)

    if config_data.persistence_type == PersistenceType.PICKLE:
        if not os.path.isdir(args.database):
            logger.error("[-] Database directory not found.")
            exit(1)
        else:
            config_data.set_pickle_directory(
                os.path.join(os.path.abspath(args.database), "data.db")
            )
            logger.info(f"[+] Pickle directory set to {config_data.pickle_path}")

    elif config_data.persistence_type == PersistenceType.POSTGRES:
        try:
            conn = psycopg.connect(config_data.get_connection_string())
            conn.close()
        except psycopg.OperationalError as e:
            logger.error("[-] Could not connect to database.")
            logger.error("f[-] Error: {e}")
            exit(1)

    logger.info("[+] Configuration loaded.")
    logger.info("[+] Starting niscoin.")

    if config_data.persistence_type == PersistenceType.PICKLE:
        logger.info("[+] Using pickle persistence.")
        persistence = PicklePersistence(config_data.pickle_path)
    elif config_data.persistence_type == PersistenceType.POSTGRES:
        logger.info("[+] Using postgres persistence.")
        persistence = PostgresPersistence(
            postgres_url=config_data.get_connection_string(),
            postgres_schema=config_data.schema,
        )

    niscoin_app = (
        Application.builder()
        .token(config_data.bot_token)
        .persistence(persistence)
        .build()
    )

    niscoin_app.add_handler(CommandHandler("start", conversation.start))
    niscoin_app.add_handler(CommandHandler("help", conversation.help))
    niscoin_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.echo)
    )
    niscoin_app.add_handler(CallbackQueryHandler(conversation.help_button))
    niscoin_app.run_polling()


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    log_file = os.path.join(log_path, "niscoin.log")
    if not os.path.isdir(log_path):
        os.mkdir(log_path)
    handler = TimedRotatingFileHandler(log_file, when="D", interval=1, backupCount=5)
    logger.addHandler(handler)
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logger.info,
    )

    main()
