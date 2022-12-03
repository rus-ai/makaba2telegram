import datetime
import requests
import json
import time
import re
import logging
import os
from types import SimpleNamespace

import urllib3
from telegram.ext import Updater, CommandHandler, ChatMemberHandler, ConversationHandler
from telegram import Update, BotCommand

from modules import command_thread_delete, command_group, command_thread_add
from modules.bot_events import track_bot_chats, track_chat_members
from modules.database import init_db, Posts, threads_cache, load_post_cache, posts_cache
from modules.settings import BOT_TOKEN, BOT_LOG_CHAT_ID, enable_picture_preview, dir_media, timeout_polling, all_dirs
from modules.settings import command_description, timeout_thread, timeout_media
from modules.settings import sleep_time, post_link, post_url, dir_store, log_file, log_formatter


updater = Updater(BOT_TOKEN)
dp = updater.dispatcher
jq = updater.job_queue

start_time = datetime.datetime.now()
log_message = None
message_count = 0


def check_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def create_dirs():
    for directory in all_dirs:
        check_dir(directory)


def cleanhtml(raw_html):
    clean_br = re.compile('<br/?>')
    clean_r = re.compile('<.*?>')
    cleantext = (re.sub(clean_r, '', re.sub(clean_br, '\n', raw_html)))\
        .replace('&gt;', '>').replace('&lt;', '<') \
        .replace("_", "\\_").replace("*", "\\*")\
        .replace("[", "\\[").replace("`", "\\`") \
        .replace("&#39;", "'").replace("&#92;", "\\").replace("&amp;", "&") \
        .replace("&quot;", "\"").replace("&#47;", "/").replace("&#95;", "\\_") \
        .replace("&#37;", "%")
    return cleantext[:3500]


def thread_request(board, thread):
    url = f'{post_url}/{board}/res/{thread}.json'
    try:
        r = requests.get(url, timeout=timeout_thread)
    except urllib3.exceptions.ReadTimeoutError:
        logging.exception('Thread request: HTTP read timeout')
        return
    except requests.exceptions.ConnectTimeout:
        logging.exception('Thread request: HTTP read timeout')
        return
    except requests.exceptions.ReadTimeout:
        logging.exception('Thread request: HTTP read timeout')
        return
    except requests.exceptions.Timeout:
        logging.exception('Thread request: HTTP connection timeout')
        return
    except TimeoutError:
        logging.exception('Timeout Error')
        return
    except requests.exceptions.HTTPError:
        logging.exception('Thread request: Invalid HTTP response')
        return
    except requests.exceptions.ConnectionError as e:
        logging.exception('Thread request: Connection error: {}'.format(e))
        return
    logging.debug(f"Status code: {r.status_code}")
    if r.status_code != 200:
        return
    try:
        r_thread = json.loads(r.text, object_hook=lambda d: SimpleNamespace(**d))
    except json.decoder.JSONDecodeError:
        logging.exception("json.decoder.JSONDecodeError")
        return
    except ValueError:
        logging.exception("ValueError")
        return
    returned_thread = str(r_thread.current_thread)
    if returned_thread != thread:
        logging.error(f"Requested thread {thread}, but returned {returned_thread}, end=" "")
        return
    return r_thread.threads[0]


def media_request(file_url, save_path):
    url = f'{post_url}/{file_url}'
    try:
        r = requests.get(url, timeout=timeout_media)
    except requests.exceptions.Timeout:
        logging.exception('HTTP connection timeout')
        return
    except requests.exceptions.HTTPError:
        logging.exception('Invalid HTTP response')
        return
    except requests.exceptions.ConnectionError as e:
        logging.exception('Connection error: {}'.format(e))
        return
    logging.debug(f"Download_file: {file_url}")
    logging.debug(f"Status code: {r.status_code}")
    if r.status_code != 200:
        return
    logging.debug(f"Saving path: {save_path}")
    with open(save_path, mode='wb') as local_file:
        local_file.write(r.content)


def media_download(board, thread, post):
    for file in post.files:
        directory = os.path.join(dir_media, board, thread)
        check_dir(directory)
        media_request(file.path, os.path.join(directory, f"{post.num}_{file.name}"))


def send_telegram(text: str, channel_id: str, no_preview: bool):
    global message_count
    try:
        message = updater.bot.send_message(
            chat_id=channel_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=no_preview
        )
    except Exception as e:
        logging.exception(f"Telegram post fail: {e}")
        return None
    message_count += 1
    post_number = message.message_id
    return post_number


def do_job_item(board, thread, chanel):
    if not posts_cache.get(board, {thread: None}).get(thread):
        load_post_cache(board, thread)
    thread_json = None
    try:
        logging.debug(f"Request... {str(board)} {str(thread)}")
        thread_json = thread_request(str(board), str(thread))
    except requests.exceptions.ChunkedEncodingError:
        logging.exception("Chunk error")
        return
    except requests.exceptions.ConnectionError:
        logging.exception("Connection error")
        return
    finally:
        logging.debug("Requested")
        if thread_json is None:
            for thread_dict in threads_cache:
                if thread_dict.get("thread") == thread and thread_dict.get("board") == board:
                    thread_dict["status"] = "404"
            logging.debug("Empty thread")
        if thread_json:
            for thread_dict in threads_cache:
                if thread_dict.get("thread") == thread and thread_dict.get("board") == board:
                    thread_dict["status"] = "200"
                    thread_dict["count"] = len(thread_json.posts)
            logging.debug(f"Thread found, post count: {len(thread_json.posts)}")
            for post in thread_json.posts:
                if posts_cache.get(board).get(thread).get(str(post.num), 0) == 0:
                    time.sleep(sleep_time)
                    text = ''
                    if post.files:
                        text += '🎨'
                        count = 0
                        for f in post.files:
                            count = count + 1
                            text += f' [{count}]({post_url}{f.path})'
                        text += '\n'
                    post_date = post.date

                    with open(os.path.join(dir_store, f"{post.num}.html"), "w", encoding="utf-8") as f:
                        f.write(post.comment)

                    post_body = cleanhtml(post.comment)

                    links = [link_obj.group() for link_obj in post_link.finditer(post_body)]
                    for link in set(links):
                        logging.debug(f"Searching link: {link[2:]}")
                        message_lnk = posts_cache.get(board).get(thread).get(str(link[2:]), None)
                        if message_lnk:
                            t_me = f"https://t.me/{chanel[1:]}/{message_lnk}"
                            logging.debug(f"Found: {t_me}")
                            post_body = post_body.replace(link, f"[{link}]({t_me})")

                    text += f'{post_body}\n'
                    text += f'{post_date} | [{post.num}]({post_url}/{str(board)}/res/{str(thread)}.html#{post.num})'
                    disable_preview = True
                    if enable_picture_preview:
                        if post.files:
                            disable_preview = False
                    with open(os.path.join(dir_store, f"{post.num}.markdown"), "w", encoding="utf-8") as f:
                        f.write(text)
                    message_id = send_telegram(text, chanel, disable_preview)
                    if message_id:
                        Posts.create(board=board, thread=thread, post=post.num, message=message_id)
                        posts_cache[board][thread][str(post.num)] = str(message_id)
                        for thread_dict in threads_cache:
                            if thread_dict.get("thread") == thread and thread_dict.get("board") == board:
                                thread_dict["last"] = f"{datetime.datetime.now():%y.%m.%d %H:%M:%S}"
                    if post.files:
                        media_download(board, thread, post)


def do_all_jobs():
    for thread in threads_cache:
        do_job_item(thread.get("board"), thread.get("thread"), thread.get("group"))
    logging.debug("All jobs complete")


def start_bot(update, _):
    update.message.reply_text(f"Chat ID: {update.message.chat.id}")


def send_bot_log(_):
    global log_message
    text = f"Started: {start_time:%y.%m.%d %H:%M:%S}\n"
    text += f"Last: {datetime.datetime.now():%y.%m.%d %H:%M:%S}\n"
    text += f"Count: {message_count}\n\n"
    for thread in threads_cache:
        status = "⚠"
        if thread.get("status") == "200":
            status = "✅"
        if thread.get("status") == "404":
            status = "⛔"
        text += f"{thread.get('board')}\\{thread.get('thread')}->{thread.get('group')[1:]}\n"
        text += f"{status} [{thread.get('count')}] {thread.get('last')}\n"
    if log_message:
        try:
            updater.bot.edit_message_text(
                chat_id=BOT_LOG_CHAT_ID,
                message_id=log_message.message_id,
                text=text
            )
        except Exception as e:
            logging.error(f"Editing log message failed: {repr(e)} {str(e)}")
            if str(e) == "Message to edit not found":
                logging.error("Next time will be created new log message")
                log_message = None
    else:
        try:
            log_message = updater.bot.send_message(
                chat_id=BOT_LOG_CHAT_ID,
                text=text
            )
        finally:
            pass
    do_all_jobs()


def describe_command_handler(command_list, command_handler):
    if isinstance(command_handler, CommandHandler):
        for command in command_handler.command:
            command_list.append(BotCommand(command=command,
                                           description=command_description.get(command, 'Not described')))


def set_command_helper():
    command_list = []
    dp.bot.delete_my_commands()
    for handler in dp.handlers.get(0):
        describe_command_handler(command_list, handler)
        if isinstance(handler, CommandHandler):
            describe_command_handler(command_list, handler)
        elif isinstance(handler, ConversationHandler):
            for entry in handler.entry_points:
                describe_command_handler(command_list, entry)
    dp.bot.set_my_commands(command_list)


def start_telegram_bot():
    dp.add_handler(CommandHandler('start', start_bot))
    dp.add_handler(command_group.command_group_handler)
    dp.add_handler(command_thread_add.command_thread_add_handler)
    dp.add_handler(command_thread_delete.command_thread_delete_handler)
    dp.add_handler(ChatMemberHandler(track_bot_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    dp.add_handler(ChatMemberHandler(track_chat_members, ChatMemberHandler.CHAT_MEMBER))
    set_command_helper()
    jq.run_repeating(send_bot_log, interval=60, first=10)
    while True:
        try:
            updater.start_polling(timeout=timeout_polling, allowed_updates=Update.ALL_TYPES)
            updater.idle()
        except Exception as e:
            logging.exception(f"Exception: {e}")


def main():
    create_dirs()
    logging.basicConfig(filename=log_file, level=logging.WARNING, format=log_formatter)
    logging.warning("Program started")
    print("Program started")
    init_db()
    start_telegram_bot()


if __name__ == "__main__":
    main()
