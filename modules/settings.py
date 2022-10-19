import os
import re
import sys
import dotenv

dotenv.load_dotenv(dotenv.find_dotenv())

BOT_TOKEN = os.getenv("BOT_TOKEN")
if BOT_TOKEN is None:
    raise Exception("Please set .env variable BOT_TOKEN.")

BOT_OWNER_ID = os.getenv("BOT_OWNER_ID", None)
if str(BOT_OWNER_ID).lstrip("-").isdigit():
    BOT_OWNER_ID = int(BOT_OWNER_ID)

BOT_LOG_CHAT_ID = os.getenv("BOT_LOG_CHAT_ID", None)
if str(BOT_LOG_CHAT_ID).lstrip("-").isdigit():
    BOT_LOG_CHAT_ID = int(BOT_LOG_CHAT_ID)

dir_path = os.path.dirname(str(sys.modules['__main__'].__file__))
dir_store = os.path.join(dir_path, 'store')
dir_media = os.path.join(dir_path, 'media')
log_file = os.path.join(dir_path, 'log', 'events.log')
events_bot_file = os.path.join(dir_path, 'events', 'bot.dict')
events_user_file = os.path.join(dir_path, 'events', 'user.dict')
log_formatter = "%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"

sleep_time = 3  # 20 messages to group in minute
enable_picture_preview = False
post_link = re.compile(">>\\d{6}")
post_url = 'https://2ch.hk'

command_description = {"start": "Start this bot",
                       "group": "Begin telegram group management dialog",
                       "add": "Subscribe new thread to telegram group",
                       "delete": "Unsubscribe thread from telegram group",
                       }

timeout_thread = 5
timeout_media = 300
timeout_polling = 15
