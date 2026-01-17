"""
对话历史管理模块 - API 路由

C++ 程序员理解：
- HTTP 接口定义
- 管理对话会话的增删查
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from .schemas import AddMessageRequest, GetHistoryResponse
from .service import history_service


def register_routes(app):
    """
    注册对话历史管理路由到主应用
    
    参数：
        app: FastAPI 应用实例
    """
    router = APIRouter(
        prefix="/history",
        tags=["对话历史管理"]
    )
    
    # ========== API 端点定义 ==========
    
    @router.post("/session")
    async def create_session(user_id: str = Header(..., alias="X-User-ID")):
        """
        创建新对话会话
        
        请求头：
            X-User-ID: 用户唯一标识
        
        返回：
            {
                "session_id": "uuid-string",
                "message": "新会话已创建"
            }
        """
        session_id = history_service.create_session(user_id)
        return {
            "session_id": session_id,
            "message": "新会话已创建"
        }
    
    @router.get("/session")
    async def get_current_session(user_id: str = Header(..., alias="X-User-ID")):
        """
        获取当前会话 ID
        
        返回：
            {
                "session_id": "uuid-string" 或 null
            }
        """
        session_id = history_service.get_current_session(user_id)
        return {"session_id": session_id}
    
    @router.post("/message")
    async def add_message(
        message_data: AddMessageRequest,
        user_id: str = Header(..., alias="X-User-ID"),
        session_id: Optional[str] = Header(None, alias="X-Session-ID")
    ):
        """
        添加消息到会话
        
        请求头：
            X-User-ID: 用户 ID
            X-Session-ID: 会话 ID（可选，不填使用当前会话）
        
        请求体：
            {
                "role": "user" 或 "assistant",
                "content": "消息内容"
            }
        
        返回：
            {
                "success": true,
                "message": "消息已添加"
            }
        """
        # 如果未指定 session_id，使用当前会话；缺省则自动创建
        if session_id is None:
            session_id = history_service.get_current_session(user_id)
            if session_id is None:
                # 自动创建新会话
                session_id = history_service.create_session(user_id)
        
        success = history_service.add_message(user_id, session_id, message_data)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {
            "success": True,
            "message": "消息已添加",
            "session_id": session_id
        }
    
    @router.get("", response_model=GetHistoryResponse)
    async def get_history(
        user_id: str = Header(..., alias="X-User-ID"),
        session_id: Optional[str] = Header(None, alias="X-Session-ID")
    ):
        """
        查询对话历史
        
        请求头：
            X-User-ID: 用户 ID
            X-Session-ID: 会话 ID（可选，不填查询当前会话）
        
        返回：
            {
                "session_id": "...",
                "messages": [...],
                "message_count": 10,
                "created_at": "2026-01-16T10:30:00",
                "updated_at": "2026-01-16T11:00:00"
            }
        """
        # 若未传入 session_id，则查询“当前会话”（最近更新）
        history = history_service.get_history(user_id, session_id)
        if not history:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        
        return history
    
    @router.delete("/session")
    async def clear_session(
        user_id: str = Header(..., alias="X-User-ID"),
        session_id: Optional[str] = Header(None, alias="X-Session-ID")
    ):
        """
        清空会话消息（保留会话）
        
        返回：
            204 No Content
        """
        if session_id is None:
            session_id = history_service.get_current_session(user_id)
            if session_id is None:
                raise HTTPException(status_code=404, detail="会话不存在")
        
        success = history_service.clear_session(user_id, session_id)
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {"message": "会话已清空"}
    
    @router.delete("/session/all")
    async def delete_all_sessions(user_id: str = Header(..., alias="X-User-ID")):
        """
        删除用户的所有会话
        
        返回：
            200 OK
        """
        history_service.delete_all_sessions(user_id)
        return {"message": "所有会话已删除"}
    
    # 将路由器挂载到主应用（保持 main.py 简洁）
    app.include_router(router)
