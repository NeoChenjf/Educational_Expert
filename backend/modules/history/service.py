"""
对话历史管理模块 - 业务逻辑（SQLite 持久化）

C++ 视角速览：
- SessionModel / MessageModel 类似两张表：会话元数据 + 消息列表。
- HistoryService 封装 CRUD；使用 SQLModel+Session，等价于 RAII 方式管理连接。
- “当前会话”策略：取该用户最近更新的一条会话（updated_at 最大）。
"""
from typing import List, Optional
from datetime import datetime
import uuid
from sqlmodel import SQLModel, Field, Session, create_engine, select
from .schemas import Message, ConversationSession, AddMessageRequest, GetHistoryResponse


class SessionModel(SQLModel, table=True):
    session_id: str = Field(primary_key=True, index=True)
    user_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MessageModel(SQLModel, table=True):
    id: int = Field(primary_key=True)
    session_id: str = Field(foreign_key="sessionmodel.session_id", index=True)
    user_id: str = Field(index=True)
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HistoryService:
    def __init__(self, db_url: str = "sqlite:///./data.db"):
        # SQLite 持久化；check_same_thread=False 允许同一进程多协程访问。
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)

    def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        model = SessionModel(session_id=session_id, user_id=user_id)
        with Session(self.engine) as session:
            session.add(model)
            session.commit()
        return session_id

    def get_current_session(self, user_id: str) -> Optional[str]:
        # 当前会话定义：最近更新的会话（updated_at 最大）。
        with Session(self.engine) as session:
            stmt = (
                select(SessionModel)
                .where(SessionModel.user_id == user_id)
                .order_by(SessionModel.updated_at.desc())
                .limit(1)
            )
            row = session.exec(stmt).first()
            return row.session_id if row else None

    def add_message(self, user_id: str, session_id: str, message_data: AddMessageRequest) -> bool:
        with Session(self.engine) as session:
            sess = session.get(SessionModel, session_id)
            if not sess or sess.user_id != user_id:
                return False
            msg = MessageModel(
                session_id=session_id,
                user_id=user_id,
                role=message_data.role,
                content=message_data.content,
                timestamp=datetime.utcnow(),
            )
            sess.updated_at = msg.timestamp
            session.add(msg)
            session.add(sess)
            session.commit()
        return True

    def get_history(self, user_id: str, session_id: Optional[str] = None) -> Optional[GetHistoryResponse]:
        with Session(self.engine) as session:
            if session_id is None:
                session_id = self.get_current_session(user_id)
                if session_id is None:
                    return None
            sess = session.get(SessionModel, session_id)
            if not sess or sess.user_id != user_id:
                return None
            msgs = (
                session.exec(
                    select(MessageModel)
                    .where(MessageModel.session_id == session_id)
                    .order_by(MessageModel.timestamp)
                ).all()
            )
            messages = [
                Message(role=m.role, content=m.content, timestamp=m.timestamp) for m in msgs
            ]
            return GetHistoryResponse(
                session_id=session_id,
                messages=messages,
                message_count=len(messages),
                created_at=sess.created_at,
                updated_at=sess.updated_at,
            )

    def get_messages_for_api(self, user_id: str, session_id: Optional[str] = None, limit: int = 10) -> List[dict]:
        history = self.get_history(user_id, session_id)
        if not history:
            return []
        messages = history.messages[-limit:]
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    def clear_session(self, user_id: str, session_id: str) -> bool:
        with Session(self.engine) as session:
            sess = session.get(SessionModel, session_id)
            if not sess or sess.user_id != user_id:
                return False
            # 清空消息表中对应会话的记录。
            session.exec(select(MessageModel).where(MessageModel.session_id == session_id))
            session.exec("DELETE FROM messagemodel WHERE session_id = :sid", {"sid": session_id})
            sess.updated_at = datetime.utcnow()
            session.add(sess)
            session.commit()
            return True

    def delete_session(self, user_id: str, session_id: str) -> bool:
        with Session(self.engine) as session:
            sess = session.get(SessionModel, session_id)
            if not sess or sess.user_id != user_id:
                return False
            # 先删消息，再删会话元数据。
            session.exec("DELETE FROM messagemodel WHERE session_id = :sid", {"sid": session_id})
            session.delete(sess)
            session.commit()
            return True

    def delete_all_sessions(self, user_id: str) -> bool:
        with Session(self.engine) as session:
            sessions = session.exec(select(SessionModel).where(SessionModel.user_id == user_id)).all()
            if not sessions:
                return False
            session_ids = [s.session_id for s in sessions]
            # 批量删除该用户下所有消息与会话。
            session.exec(
                "DELETE FROM messagemodel WHERE session_id IN (:ids)",
                {"ids": tuple(session_ids)},
            )
            for s in sessions:
                session.delete(s)
            session.commit()
            return True


history_service = HistoryService()
