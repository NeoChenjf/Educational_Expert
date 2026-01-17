"""
档案管理模块 - 业务逻辑（SQLite 持久化）

C++ 视角速览：
- ProfileModel 相当于 struct+ORM 映射，存到 SQLite。
- ProfileService 提供 CRUD，内部用 SQLModel+Session（类似 RAII 持有连接）。
- _age 是纯函数，用于计算年龄（避免在 DB 中存重复字段）。
"""
from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Session, create_engine, select
from .schemas import ChildProfileCreate, ChildProfileUpdate, ChildProfileResponse


class ProfileModel(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True, description="用户 ID")
    nickname: str
    birth_date: date
    grade: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProfileService:
    def __init__(self, db_url: str = "sqlite:///./data.db"):
        # SQLite 轻量持久化；check_same_thread=False 允许多线程访问（uvicorn worker 内的协程共享）。
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(self.engine)

    def _age(self, birth_date: date) -> int:
        # 纯计算，不依赖数据库；保持单一真值来源（生日）。
        today = date.today()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age

    def create_profile(self, user_id: str, profile_data: ChildProfileCreate) -> ChildProfileResponse:
        now = datetime.utcnow()
        model = ProfileModel(
            id=user_id,
            nickname=profile_data.nickname,
            birth_date=profile_data.birth_date,
            grade=profile_data.grade,
            notes=profile_data.notes,
            created_at=now,
            updated_at=now,
        )
        with Session(self.engine) as session:
            exists = session.get(ProfileModel, user_id)
            if exists:
                raise ValueError("profile exists")
            session.add(model)
            session.commit()
            session.refresh(model)
        return self._to_response(model)

    def get_profile(self, user_id: str) -> Optional[ChildProfileResponse]:
        with Session(self.engine) as session:
            model = session.get(ProfileModel, user_id)
            if not model:
                return None
            return self._to_response(model)

    def update_profile(self, user_id: str, update_data: ChildProfileUpdate) -> Optional[ChildProfileResponse]:
        with Session(self.engine) as session:
            model = session.get(ProfileModel, user_id)
            if not model:
                return None
            data = update_data.model_dump(exclude_unset=True)
            for k, v in data.items():
                setattr(model, k, v)
            model.updated_at = datetime.utcnow()
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_response(model)

    def delete_profile(self, user_id: str) -> bool:
        with Session(self.engine) as session:
            model = session.get(ProfileModel, user_id)
            if not model:
                return False
            session.delete(model)
            session.commit()
            return True

    def _to_response(self, model: ProfileModel) -> ChildProfileResponse:
        age = self._age(model.birth_date)
        return ChildProfileResponse(
            id=model.id,
            nickname=model.nickname,
            birth_date=model.birth_date,
            grade=model.grade,
            notes=model.notes,
            age=age,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


profile_service = ProfileService()
