from sqlmodel import Session, create_engine

engine = create_engine("sqlite:///lightnovel.db")

db_session = Session(engine)