"""
对话历史管理模块 - 数据模型

C++ 程序员理解：
- 定义消息、对话会话的数据结构
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class Message(BaseModel):
    """
    单条消息（类似 C++ struct）
    """
    role: Literal["user", "assistant", "system"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间戳")


class ConversationSession(BaseModel):
    """
    对话会话（包含多条消息）
    """
    user_id: str = Field(..., description="用户 ID")
    session_id: str = Field(..., description="会话 ID（每次新对话创建新 ID）")
    messages: List[Message] = Field(default_factory=list, description="消息列表")
    created_at: datetime = Field(default_factory=datetime.now, description="会话创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="最后更新时间")


class AddMessageRequest(BaseModel):
    """
    添加消息的请求
    """
    role: Literal["user", "assistant"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class GetHistoryResponse(BaseModel):
    """
    查询历史的响应
    """
    session_id: str
    messages: List[Message]
    message_count: int = Field(..., description="消息总数")
    created_at: datetime
    updated_at: datetime
