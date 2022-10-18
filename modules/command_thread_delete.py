import peewee
from telegram import ReplyKeyboardRemove
from telegram.ext import ConversationHandler, MessageHandler, Filters, CommandHandler

from modules.database import Threads, threads_cache
from modules.settings import BOT_OWNER_ID

BOARD_ENTER, THREAD_ENTER = range(2)


def thread_delete_board(update, context):
    name = update.message.text
    context.user_data["group"] = name
    update.message.reply_text("Enter board name:", reply_markup=ReplyKeyboardRemove())
    return BOARD_ENTER


def thread_delete_number(update, context):
    name = update.message.text
    context.user_data["board"] = name
    update.message.reply_text("Enter thread number:")
    return THREAD_ENTER


def thread_delete(update, context):
    number = update.message.text
    try:
        thread = Threads.get(Threads.board == context.user_data.get('board'), Threads.thread == number)
    except peewee.DoesNotExist:
        update.message.reply_text("Thread not exist!")
        return ConversationHandler.END
    thread.delete_instance()
    for thread_dict in threads_cache:
        if thread_dict.get("thread") == number and thread_dict.get("board") == context.user_data.get('board'):
            threads_cache.remove(thread_dict)
    update.message.reply_text(f"DELETED {context.user_data.get('board')}/{number}")
    return ConversationHandler.END


def thread_delete_cancel(update, _):
    update.message.reply_text("Threads delete canceled", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


command_thread_delete_handler = ConversationHandler(
    entry_points=[CommandHandler('delete', thread_delete_board, Filters.chat(BOT_OWNER_ID))],
    states={
        BOARD_ENTER: [
            MessageHandler(Filters.text & ~Filters.command, thread_delete_number),
            CommandHandler('skip', thread_delete_cancel),
        ],
        THREAD_ENTER: [
            MessageHandler(Filters.text & ~Filters.command, thread_delete),
            CommandHandler('skip', thread_delete_cancel),
        ],
    },
    fallbacks=[CommandHandler('cancel', thread_delete_cancel)],
)
