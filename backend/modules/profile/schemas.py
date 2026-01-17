"""
档案管理模块 - 数据模型

说明：
- 定义前后端交互的数据结构（Pydantic BaseModel），用于请求/响应验证与文档生成。
- 运行时计算字段（如年龄）不入库，保持单一真值来源（生日）。
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class ChildProfileBase(BaseModel):
    """
    孩子档案基础数据（请求/响应共享的公共字段）
    """
    nickname: str = Field(..., description="孩子昵称")
    birth_date: date = Field(..., description="出生日期")
    grade: Optional[str] = Field(None, description="年级（可选）")
    notes: Optional[str] = Field(None, description="备注信息（可选）")


class ChildProfileCreate(ChildProfileBase):
    """
    创建档案的请求数据（继承基础数据）
    """
    pass


class ChildProfileUpdate(BaseModel):
    """
    更新档案的请求数据（所有字段可选，用于部分更新）
    """
    nickname: Optional[str] = None
    birth_date: Optional[date] = None
    grade: Optional[str] = None
    notes: Optional[str] = None


class ChildProfileResponse(ChildProfileBase):
    """
    返回给前端的档案数据（包含计算字段，如年龄）
    """
    id: str = Field(..., description="档案 ID（用户唯一标识）")
    age: int = Field(..., description="当前年龄（自动计算）")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        # 允许从 ORM 对象转换（如果以后接入数据库），
        # 便于后续将 SQLModel/ORM 实体直接转换为响应模型。
        from_attributes = True
