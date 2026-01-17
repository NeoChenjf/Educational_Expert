"""
聊天适配器模块

作用：对外提供聚合接口 /chat_with_context
- 自动读取档案年龄
- 自动读取并裁剪历史
- 转调既有 /chat 接口（不改动 main.py 逻辑）
- 自动回写历史（user/assistant 两条）
"""

from .routes import register_routes

__all__ = ["register_routes"]
