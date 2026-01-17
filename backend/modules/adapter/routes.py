"""
聊天适配器模块 - API 路由

模块定位：
- 充当“编排层/门面”，为前端提供一站式接口 `POST /chat_with_context`：
    - 自动获取孩子档案（年龄）
    - 自动获取会话历史（最近 N 条）
    - 将用户消息先写入历史以保证对账
    - 转调既有 `/chat`（保留原业务与安全策略）
    - 回写 AI 回复到历史

设计原则：
- 不侵入主应用逻辑：通过 `httpx` 调用已有 `/chat`，避免复制核心业务。
- 会话与用户通过请求头传递：`X-User-ID` 必填，`X-Session-ID` 可选（缺省则自动创建/复用）。
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, Literal
import httpx

from modules.profile.service import profile_service
from modules.history.service import history_service
from modules.history.schemas import AddMessageRequest
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal
import httpx

from modules.profile.service import profile_service
from modules.history.service import history_service
from modules.history.schemas import AddMessageRequest


class ChatAdapterRequest(BaseModel):
    message: str = Field(..., description="家长提问")
    response_mode: Literal["concise", "detailed"] = Field(
        default="concise", description="回答模式：concise/detailed"
    )
    history_limit: int = Field(10, ge=0, le=20, description="取最近N条历史用于上下文")


class ChatAdapterResponse(BaseModel):
    session_id: str
    reply: str


def register_routes(app):
    router = APIRouter(prefix="/chat_with_context", tags=["聊天适配器"])

    @router.post("", response_model=ChatAdapterResponse)
    async def chat_with_context(
        payload: ChatAdapterRequest,
        user_id: str = Header(..., alias="X-User-ID"),
        session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    ):
        """
        编排流程说明：
        1) 会话准备：复用传入的 `X-Session-ID`；若缺失则获取当前会话或创建新会话。
        2) 上下文收集：读取最近 `history_limit` 条消息，并获取档案年龄（若存在）。
        3) 先写入用户消息到历史：保证请求与历史一致性，便于后续审计/回放。
        4) 转调 `/chat`：保留既有的安全过滤与生成策略，不在适配层重复实现。
        5) 回写 AI 回复到历史：形成完整的双向消息记录。
        6) 返回 `session_id` 与 `reply`：供前端缓存与展示。

        头部约定：
        - X-User-ID：必填，用于区分用户并路由到其档案与历史。
        - X-Session-ID：可选，用于定位具体会话；缺省时自动创建/复用。
        """
        # 1) 准备会话
        if session_id is None:
            session_id = history_service.get_current_session(user_id)
            if session_id is None:
                session_id = history_service.create_session(user_id)

        # 2) 取历史 & 档案年龄
        history = history_service.get_messages_for_api(
            user_id, session_id, limit=payload.history_limit
        )
        profile = profile_service.get_profile(user_id)
        age = profile.age if profile else None

        # 3) 回写用户消息到历史（先写，保证对账与一致性）
        history_service.add_message(
            user_id,
            session_id,
            message_data=AddMessageRequest(role="user", content=payload.message),
        )

        # 4) 调用现有 /chat（复用既有逻辑与安全策略）
        try:
            # 直接转调本机已有的 /chat，避免复制业务逻辑与安全策略
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "http://127.0.0.1:8000/chat",
                    json={
                        "message": payload.message,
                        "response_mode": payload.response_mode,
                        "child_age": age,
                        "history": history,
                    },
                )
        except httpx.RequestError as e:
            # 转调失败（网络/服务不可用）→ 返回 503
            raise HTTPException(status_code=503, detail=f"聊天服务不可用: {e}")

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        data = resp.json()
        reply = data.get("reply", "")

        # 5) 回写 AI 回复（形成完整的双向记录）
        history_service.add_message(
            user_id,
            session_id,
            message_data=AddMessageRequest(role="assistant", content=reply),
        )

        return ChatAdapterResponse(session_id=session_id, reply=reply)

    app.include_router(router)
