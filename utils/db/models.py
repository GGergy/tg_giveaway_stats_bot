import sqlalchemy
from sqlalchemy.orm import relationship, sessionmaker

from utils.db.connect import SqlAlchemyBase, create_connection
from utils.config import settings


class ChannelToGiveaway(SqlAlchemyBase):
    __tablename__ = 'channel_to_giveaway'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    channel_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('channels.name'))
    giveaway_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('giveaways.id'))



class User(SqlAlchemyBase):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    username = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    notifies = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    giveaways = relationship("Giveaway", cascade="delete, all")


class Channel(SqlAlchemyBase):
    __tablename__ = 'channels'

    name = sqlalchemy.Column(sqlalchemy.String, primary_key=True, unique=True)


class Giveaway(SqlAlchemyBase):
    __tablename__ = 'giveaways'
    __table_args__ = (sqlalchemy.UniqueConstraint('chat_id', 'message_id'),)

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String)
    end_date = sqlalchemy.Column(sqlalchemy.DateTime)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    chat_id = sqlalchemy.Column(sqlalchemy.Integer)
    message_id = sqlalchemy.Column(sqlalchemy.Integer)
    channels = relationship("Channel", secondary='channel_to_giveaway', backref="giveaways")


conn: sessionmaker = create_connection(settings.db_file)
