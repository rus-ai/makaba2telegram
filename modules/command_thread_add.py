from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, MessageHandler, Filters, CommandHandler

from modules.database import Groups, Threads, threads_cache
from modules.settings import BOT_OWNER_ID

GROUP_ENTER, BOARD_ENTER, THREAD_ENTER = range(3)


def thread_group(update, _):
    keyboard = []
    for group in Groups.select():
        keyboard.append([group.group])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)
    update.message.reply_text("Select group to post thread:", reply_markup=reply_markup)
    return GROUP_ENTER


def thread_board(update, context):
    name = update.message.text
    context.user_data["group"] = name
    update.message.reply_text("Enter board name:", reply_markup=ReplyKeyboardRemove())
    return BOARD_ENTER


def thread_number(update, context):
    name = update.message.text
    context.user_data["board"] = name
    update.message.reply_text("Enter thread number:")
    return THREAD_ENTER


def thread_add(update, context):
    number = update.message.text
    Threads.create(board=context.user_data.get('board'),
                   group=context.user_data.get('group'),
                   thread=number,
                   status="0",
                   count="0",
                   last="never")
    threads_cache.append({"board": context.user_data.get('board'),
                          "group": context.user_data.get('group'),
                          "thread": number,
                          "status": "0",
                          "count": "0",
                          "last": "never",
                          })
    update.message.reply_text(f"ADDED {context.user_data.get('board')}/{number} -> {context.user_data.get('group')}")
    return ConversationHandler.END


def thread_cancel(update, _):
    update.message.reply_text("Threads adding canceled", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


command_thread_add_handler = ConversationHandler(
    entry_points=[CommandHandler('add', thread_group, Filters.chat(BOT_OWNER_ID))],
    states={
        GROUP_ENTER: [
            MessageHandler(Filters.text & ~Filters.command, thread_board),
            CommandHandler('skip', thread_cancel),
        ],
        BOARD_ENTER: [
            MessageHandler(Filters.text & ~Filters.command, thread_number),
            CommandHandler('skip', thread_cancel),
        ],
        THREAD_ENTER: [
            MessageHandler(Filters.text & ~Filters.command, thread_add),
            CommandHandler('skip', thread_cancel),
        ],
    },
    fallbacks=[CommandHandler('cancel', thread_cancel)],
)
