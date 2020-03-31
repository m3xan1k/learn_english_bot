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
    name = pw.CharField(null=True)
    created_at = pw.DateField(default=datetime.date.today())


class UserPair(BaseModel):
    user = pw.ForeignKeyField(User, backref='users_pairs')
    pair = pw.ForeignKeyField(Pair, backref='users_pairs')

    class Meta:
        primary_key = pw.CompositeKey('user', 'pair')


def create_tables():
    with db:
        db.create_tables([User, Pair, UserPair])


if __name__ == '__main__':
    pass
