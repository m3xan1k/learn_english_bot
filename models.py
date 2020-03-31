import datetime

import peewee as pw


# using sqlite for dedvelopment
db = pw.SqliteDatabase('test.db')


class BaseModel(pw.Model):
    class Meta:
        database = db


class Pair(BaseModel):
    russian_word = pw.CharField()
    english_word = pw.CharField()


class User(BaseModel):
    chat_id = pw.IntegerField()
    name = pw.CharField()
    created_at = pw.DateField(default=datetime.date.today())


class UserPair(BaseModel):
    user = pw.ForeignKeyField(User, backref='users_pairs')
    pair = pw.ForeignKeyField(Pair, backref='users_pairs')
