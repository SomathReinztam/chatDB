from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, JSON, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass

# TODO:  refactorizar los modelos para que db_credentials este en ChatModel
class UserModel(Base):
    __tablename__ = "user2"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    db_credentials = Column(JSON)



class ChatModel(Base):
    __tablename__ = "chat"
    chat_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user2.user_id"), nullable=False)
    #db_credentials = Column(JSON)

    user = relationship("UserModel", backref="chats")



class MessageModel(Base):
    __tablename__ = "message"
    message_id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("user2.user_id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chat.chat_id"), nullable=False)

    role = Column(String)
    content = Column(JSON)
    date = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("UserModel", backref="message")
    chat = relationship("ChatModel", backref="message")



