import peewee
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, MessageHandler, Filters, CommandHandler

from modules.database import Groups
from modules.settings import BOT_OWNER_ID

GROUP_LIST, GROUP_ADD, GROUP_DELETE, GROUP_EDIT = range(4)


def groups_start(update, context):
    keyboard = [["New group"]]
    for group in Groups.select():
        keyboard.append([group.group])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("Select group for edit/delete or create new one:", reply_markup=reply_markup)
    return GROUP_LIST


def groups_edit(update, context):
    name = update.message.text
    if name == "New group":
        update.message.reply_text("Enter group name:", reply_markup=ReplyKeyboardRemove())
        return GROUP_ADD
    if Groups.select().where(Groups.group == name):
        update.message.reply_text(f"Retype group name to delete group {name}:", reply_markup=ReplyKeyboardRemove())
        return GROUP_DELETE
    update.message.reply_text("Group not exist!")
    return ConversationHandler.END


def groups_add(update, context):
    name = update.message.text
    if name[0] != "@":
        name = "@" + name
    Groups.create(group=name)
    update.message.reply_text(f"Group {name} created!")
    return ConversationHandler.END


def groups_delete(update, context):
    name = update.message.text
    if name[0] != "@":
        name = "@" + name
    try:
        group = Groups.get(Groups.group == name)
    except peewee.DoesNotExist:
        update.message.reply_text("Group not exist!")
        return ConversationHandler.END
    group.delete_instance()
    update.message.reply_text(f"Group {name} deleted!")
    return ConversationHandler.END


def groups_cancel(update, context):
    update.message.reply_text("Groups editing canceled", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


command_group_handler = ConversationHandler(
    entry_points=[CommandHandler('group', groups_start, Filters.chat(BOT_OWNER_ID))],
    states={
        GROUP_LIST: [
            MessageHandler(Filters.text & ~Filters.command, groups_edit),
            CommandHandler('skip', groups_cancel),
        ],
        GROUP_ADD: [
            MessageHandler(Filters.text & ~Filters.command, groups_add),
            CommandHandler('skip', groups_cancel),
        ],
        GROUP_DELETE: [
            MessageHandler(Filters.text & ~Filters.command, groups_delete),
            CommandHandler('skip', groups_cancel),
        ],
    },
    fallbacks=[CommandHandler('cancel', groups_cancel)],
)
