from ast import literal_eval
from datetime import datetime

from telegram import ChatMember, Chat

from modules.settings import events_bot_file, events_user_file


def write_event(file, event):
    with open(file, "a", encoding="utf-8") as f:
        f.write(event)


def extract_status_change(chat_member_update):
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))
    if status_change is None:
        return None
    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.CREATOR,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.CREATOR,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)
    return was_member, is_member


def track_bot_chats(update, _) -> None:
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result
    cause_name = update.effective_user
    chat = update.effective_chat
    time = datetime.now()
    event = {'timestamp': time.timestamp(),
             'time': time.isoformat(timespec='seconds', sep=' '),
             'action': None,
             'user': literal_eval(f'{cause_name}'),
             'chat': literal_eval(f'{chat}')}
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            event['action'] = "start_bot"
        elif was_member and not is_member:
            event['action'] = "block_bot"
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            event['action'] = "add_group"
        elif was_member and not is_member:
            event['action'] = "remove_group"
    else:
        if not was_member and is_member:
            event['action'] = "add_channel"
        elif was_member and not is_member:
            event['action'] = "remove_channel"
    write_event(events_bot_file, f'{event}\n')


def track_chat_members(update, _):
    cause_name = update.chat_member.from_user
    member_name = update.chat_member.new_chat_member.user
    chat = update.effective_chat
    time = datetime.now()
    _, new_status = update.chat_member.difference().get("status")
    event = {'timestamp': time.timestamp(),
             'time': time.isoformat(timespec='seconds', sep=' '),
             'action': new_status,
             'user': literal_eval(f'{member_name}'),
             'chat': literal_eval(f'{chat}'),
             'admin': literal_eval(f'{cause_name}')}
    write_event(events_user_file, f'{event}\n')
