import traceback

from sqlmodel import SQLModel, create_engine, select, Session, Field

from logs import get_logger


logger = get_logger()
engine = create_engine("sqlite:///banned.db")


class Banned(SQLModel, table=True):
    no: int = Field(primary_key=True)
    chat_id: int
    username: str | None = None
    tried_unban: bool = False


def ban(chat_id: int, username: str | None = None) -> bool:
    try:
        query = select(Banned).where(Banned.chat_id == chat_id)
        with Session(engine) as s:
            res = s.exec(query).first()
            if not res:
                new = Banned(chat_id=chat_id, username=username)
                s.add(new)
                s.commit()
        return True
    except Exception as err:
        logger.error(f"Ошибка бана: {err}")
        logger.error(traceback.format_exc())
        return False


def unban(chat_id: int) -> bool:
    try:
        query = select(Banned).where(Banned.chat_id == chat_id)
        with Session(engine) as s:
            res = s.exec(query).first()
            if res:
                s.delete(res)
                s.commit()
                return True
    except Exception as err:
        logger.error(f"Ошибка разбана: {err}")
        return False


def check(chat_id: int) -> bool:
    query = select(Banned).where(Banned.chat_id == chat_id)
    with Session(engine) as s:
        res = s.exec(query).first()
    return res is not None

def check_unbans(chat_id: int) -> bool:
    query = select(Banned).where(Banned.chat_id == chat_id)
    with Session(engine) as s:
        res = s.exec(query).first()
    if res:
        return res.tried_unban
    return False


def user_tried_unban(chat_id: int) -> None:
    query = select(Banned).where(Banned.chat_id == chat_id)
    with Session(engine) as s:
        res = s.exec(query).first()
        if res:
            res.tried_unban = True
            s.add(res)
            s.commit()


def banlist() -> list[Banned]:
    with Session(engine) as s:
        res = s.exec(select(Banned)).all()
    return res


def create_tables() -> None:
    """Created baseline tables if they do not exist already."""
    SQLModel.metadata.create_all(engine)