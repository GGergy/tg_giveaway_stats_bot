from sqlalchemy import create_engine, orm

from utils.config import settings

SqlAlchemyBase = orm.declarative_base()


def create_connection(name):
    connection = f'sqlite:///{name}?check_same_thread=False'
    engine = create_engine(connection, echo=False)
    session_generator = orm.sessionmaker(bind=engine)
    SqlAlchemyBase.metadata.create_all(engine)
    return session_generator

