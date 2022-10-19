import os.path
import peewee

from modules.settings import dir_db

posts_db = peewee.SqliteDatabase(os.path.join(dir_db, 'posts.db'))
groups_db = peewee.SqliteDatabase(os.path.join(dir_db, 'groups.db'))
threads_db = peewee.SqliteDatabase(os.path.join(dir_db, 'threads.db'))

threads_cache = []
posts_cache = dict()


class Posts(peewee.Model):
    board = peewee.CharField()
    thread = peewee.CharField()
    post = peewee.CharField()
    message = peewee.CharField()

    class Meta:
        database = posts_db


class Groups(peewee.Model):
    group = peewee.CharField()

    class Meta:
        database = groups_db


class Threads(peewee.Model):
    board = peewee.CharField()
    thread = peewee.CharField()
    group = peewee.CharField()
    status = peewee.CharField()
    count = peewee.CharField()
    last = peewee.CharField()

    class Meta:
        database = threads_db


def load_tread_cache():
    threads = Threads.select()
    for thread in threads:
        threads_cache.append({"board": thread.board,
                              "thread": thread.thread,
                              "group": thread.group,
                              "status": "0",
                              "count": "0",
                              "last": "never",
                              })


def load_post_cache(board, thread):
    if board not in posts_cache:
        posts_cache[board] = dict()
    if thread not in posts_cache[board]:
        posts_cache[board][thread] = dict()
    posts = Posts.select().where(Posts.board == board, Posts.thread == thread)
    for post in posts:
        posts_cache[board][thread][post.post] = post.message


def init_db():
    Posts.create_table()
    Groups.create_table()
    Threads.create_table()
    load_tread_cache()
