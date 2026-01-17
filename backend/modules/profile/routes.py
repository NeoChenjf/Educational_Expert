"""
档案管理模块 - API 路由

C++ 程序员理解：
- 这个文件定义 HTTP 接口（类似 RESTful API 的 endpoint）
- register_routes 是模块的注册函数（类似插件系统的 register）
- 通过这个函数把路由挂载到主 app 上
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from .schemas import ChildProfileCreate, ChildProfileUpdate, ChildProfileResponse
from .service import profile_service


def register_routes(app):
    """
    注册档案管理路由到主应用
    
    C++ 类比：
    void register_routes(FastAPI& app) {
        app.add_route("/profile", get_profile_handler);
        app.add_route("/profile", create_profile_handler);
    }
    
    参数：
        app: FastAPI 应用实例
    """
    # 创建路由器（类似子模块的路由表）
    router = APIRouter(
        prefix="/profile",  # 所有路由前缀：/profile
        tags=["档案管理"]    # API 文档分组标签
    )
    
    # ========== API 端点定义 ==========
    
    @router.get("", response_model=ChildProfileResponse)
    async def get_profile(user_id: str = Header(..., alias="X-User-ID")):
        """
        查询孩子档案
        
        请求头：
            X-User-ID: 用户唯一标识（设备 ID 或账号）
        
        返回：
            档案完整信息
        
        C++ 理解：
            类似 HTTP GET /profile 的处理函数
            参数从 HTTP Header 中读取
        """
        profile = profile_service.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="档案不存在")
        return profile
    
    @router.post("", response_model=ChildProfileResponse)
    async def create_profile(
        profile_data: ChildProfileCreate,
        user_id: str = Header(..., alias="X-User-ID")
    ):
        """
        创建孩子档案
        
        请求头：
            X-User-ID: 用户唯一标识
        
        请求体：
            {
                "nickname": "小明",
                "birth_date": "2017-05-20",
                "grade": "一年级",
                "notes": "性格活泼"
            }
        
        返回：
            创建的档案信息（包含计算的年龄）
        """
        # 检查是否已存在
        existing = profile_service.get_profile(user_id)
        if existing:
            raise HTTPException(status_code=400, detail="档案已存在，请使用 PUT 更新")
        
        # 创建档案
        return profile_service.create_profile(user_id, profile_data)
    
    @router.put("", response_model=ChildProfileResponse)
    async def update_profile(
        update_data: ChildProfileUpdate,
        user_id: str = Header(..., alias="X-User-ID")
    ):
        """
        更新孩子档案
        
        请求体：可以只包含需要更新的字段
            {
                "nickname": "小明明"  // 只更新昵称
            }
        
        返回：
            更新后的完整档案
        """
        profile = profile_service.update_profile(user_id, update_data)
        if not profile:
            raise HTTPException(status_code=404, detail="档案不存在")
        return profile
    
    @router.delete("", status_code=204)
    async def delete_profile(user_id: str = Header(..., alias="X-User-ID")):
        """
        删除孩子档案
        
        返回：
            204 No Content（成功删除，无返回内容）
        """
        success = profile_service.delete_profile(user_id)
        if not success:
            raise HTTPException(status_code=404, detail="档案不存在")
    
    # 将路由器挂载到主应用（保持 main.py 简洁）
    # 类似 C++: app.include_router(router)
    app.include_router(router)
