"""
教育专家 AI - 后端服务主入口

功能说明：
- 提供 POST /chat 接口，接收家长问题并返回育儿建议
- 支持详细/简洁两种回答模式
- 根据孩子年龄自适应调整回答策略
- 内置安全过滤机制，防止不当建议
- 自动限制对话历史长度，优化 token 使用

技术栈：
- FastAPI: Web 框架
- OpenAI SDK: LLM 调用（兼容 Qwen 等模型）
- Pydantic: 数据验证

作者：AI 教育项目组
创建时间：2026年1月
最后更新：2026年1月14日（Phase 2 完成）
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from typing import List, Optional
import json

# 导入配置文件（包含 API Key、模型名称、System Prompt 生成逻辑等）
from config import settings

# ============== FastAPI 应用初始化 ==============

# 创建 FastAPI 应用实例
# 自动生成 API 文档：http://localhost:8000/docs (Swagger UI)
app = FastAPI(
    title="教育专家 AI",
    description="面向家长的育儿咨询 AI 助手",
    version="1.0.0"
)

# 配置跨域资源共享（CORS）
# 允许前端（Web/Mobile）从不同域名访问后端 API
# 生产环境建议限制 allow_origins 为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法（GET, POST, PUT, DELETE 等）
    allow_headers=["*"],  # 允许所有请求头
)

# 初始化 OpenAI 客户端
# 兼容 OpenAI 接口格式的其他模型（Qwen、DeepSeek 等）
# API Key 和 Base URL 从 .env 文件中读取
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,  # API 密钥
    base_url=settings.OPENAI_BASE_URL,  # API 基地址（支持自定义）
    timeout=60.0,  # 请求超时时间（秒），防止长时间等待
)


# ============== 数据模型定义 ==============

class Message(BaseModel):
    """
    单条对话消息
    
    用于表示对话历史中的一条消息，包括角色和内容。
    对话历史在 API 请求中以数组形式传递。
    
    属性：
        role: 消息角色，"user"（家长）或 "assistant"（AI）
        content: 消息内容文本
    """
    role: str  # "user" 或 "assistant"
    content: str  # 消息内容


class ChatRequest(BaseModel):
    """
    聊天请求模型
    
    定义了客户端发送给 /chat 接口的请求数据结构。
    所有字段都经过 Pydantic 自动验证。
    
    属性：
        message: 家长当前提出的问题（必填）
        history: 历史对话记录，用于多轮对话上下文（可选）
                建议最多传递 10 条消息（5 轮对话），后端会自动截断
        response_mode: 回答模式（可选，默认 "detailed"）
                      - "detailed": 详细模式，包含完整分析、心理学原理、话术、避坑提醒
                      - "concise": 简洁模式，200-300字核心建议
        child_age: 孩子年龄（可选）
                  传递后会根据年龄段自适应调整回答策略：
                  - 0-3岁：关注安全感、情绪识别
                  - 3-6岁：自我控制、同理心
                  - 6-12岁：责任感、学习习惯
                  - 12岁以上：自主性、价值观形成
    
    示例：
        {
          "message": "孩子7岁不肯写作业怎么办？",
          "response_mode": "detailed",
          "child_age": 7,
          "history": []
        }
    """
    message: str  # 用户当前输入（必填）
    history: Optional[List[Message]] = []  # 历史对话记录（可选）
    response_mode: Optional[str] = "concise"  # 回答模式（可选，默认简洁）
    child_age: Optional[int] = None  # 孩子年龄（可选）


class ChatResponse(BaseModel):
    """
    聊天响应模型
    
    定义了 /chat 接口返回的数据结构（非流式响应）。
    
    属性：
        reply: AI 生成的育儿建议内容
               如果检测到敏感词汇，会在末尾自动追加安全提醒
    """
    reply: str  # AI 回答内容


# ============== 安全过滤 ==============

def filter_unsafe_content(text: str) -> str:
    """
    后端安全过滤函数（双保险机制的第二层）
    
    功能说明：
    1. 检查 AI 回答中是否包含敏感词汇（体罚、暴力相关）
    2. 如果检测到，在原回答末尾追加安全提醒（不替换原文）
    3. 此函数作为 System Prompt 的补充防线
    
    设计理念：
    - System Prompt 已明确禁止 AI 给出体罚建议（第一层防护）
    - AI 通常会正确遵守 Prompt，说明错误做法时也是为了教育
    - 简单关键词拦截会误杀（如 AI 说"不应该打孩子"也会被检测）
    - 因此采用"追加提醒"而非"完全拦截"策略
    
    策略演进：
    - 初版：检测到关键词直接替换全文为警告
    - 问题：AI 本身不会给不当建议，却被误杀
    - 优化：保留 AI 专业回答，末尾追加安全提醒
    
    参数：
        text: AI 生成的原始回答文本
    
    返回：
        如果包含敏感词汇：原文 + 安全提醒
        如果不包含：原文不变
    
    测试案例：
        输入：家长问"孩子不听话，是不是该打他？"
        AI 回答：详细的非暴力沟通建议（包含"打"字是为了说明错误做法）
        本函数：检测到"打"，追加安全提醒，不删除专业建议
    """
    # 敏感关键词列表（体罚、暴力相关词汇）
    # 这些词汇在育儿建议中应谨慎对待
    dangerous_keywords = [
        "打", "骂", "揍", "体罚", "关禁闭", "罚站", "罚跪",
        "暴力", "殴打", "掌掴", "用力", "狠狠", "教训"
    ]
    
    # 检查回答中是否包含任何敏感词汇
    # 使用 any() 提高效率，发现一个即停止
    contains_sensitive = any(keyword in text for keyword in dangerous_keywords)
    
    if contains_sensitive:
        # 在原回答末尾追加安全提醒（不替换原内容）
        safety_reminder = (
            "\n\n---\n\n"
            "⚠️ **安全提醒**：\n\n"
            "我们坚持：任何形式的体罚或语言暴力都不应该被使用。"
            "如果上述回答中涉及相关词汇，仅为说明错误做法，请勿模仿。\n\n"
            "正确的教育方式应该是：\n"
            "• 非暴力沟通\n"
            "• 尊重孩子的人格和尊严\n"
            "• 用温和而坚定的态度设立界限\n\n"
            "如情况复杂，建议寻求专业心理咨询师帮助。"
        )
        return text + safety_reminder
    
    return text


# ============== API 接口 ==============

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    核心 API 接口：育儿咨询对话
    
    功能：
    1. 接收家长的育儿问题
    2. 根据请求参数动态生成 System Prompt
    3. 调用 LLM 生成专业育儿建议
    4. 进行安全过滤并返回结果
    
    请求示例：
        POST http://localhost:8000/chat
        {
          "message": "孩子7岁不肯写作业怎么办？",
          "response_mode": "detailed",
          "child_age": 7,
          "history": []
        }
    
    响应示例：
        {
          "reply": "亲爱的家长，我能感受到...[详细育儿建议]"
        }
    
    错误处理：
        - 如果 LLM 调用失败，返回 500 错误和错误信息
        - 所有异常都会被捕获并返回友好提示
    
    性能优化：
        - 自动限制 history 长度（最多 10 条消息）
        - 超时设置 60 秒
    
    参数：
        request: ChatRequest 对象（自动验证）
    
    返回：
        ChatResponse 对象，包含 AI 生成的回答
    
    异常：
        HTTPException: LLM 调用失败时抛出 500 错误
    """
    try:
        # ========== 步骤 1：生成动态 System Prompt ==========
        # 根据 response_mode（详细/简洁）和 child_age（年龄段）
        # 动态生成最合适的 System Prompt
        system_prompt = settings.get_system_prompt(
            mode=request.response_mode,  # "detailed" 或 "concise"
            child_age=request.child_age  # 可选，None 表示不指定年龄
        )
        
        # ========== 步骤 2：构建完整的消息列表 ==========
        # 消息列表结构：[System Prompt, 历史消息..., 当前用户消息]
        # 这是 LLM API 的标准输入格式
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话（自动限制长度）
        # 原因：防止历史过长导致：
        # 1. Token 数超限（大多数模型有 token 限制）
        # 2. API 成本增加（token 越多费用越高）
        # 3. 响应速度变慢（处理时间增加）
        max_history_messages = settings.MAX_HISTORY_ROUNDS * 2  # 5轮 = 10条消息 (user + assistant)
        
        # 使用负索引切片获取最近的消息
        # 如果 history 长度 <= max_history_messages，全部保留
        # 如果 history 长度 > max_history_messages，只保留最后 N 条
        recent_history = request.history[-max_history_messages:] if len(request.history) > max_history_messages else request.history
        
        # 将历史消息转换为 LLM API 所需的格式
        for msg in recent_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # 添加当前用户消息（最新的问题）
        messages.append({"role": "user", "content": request.message})
        
        # ========== 步骤 3：调用 LLM API ==========
        # 使用 OpenAI SDK 调用大模型（兼容 Qwen、DeepSeek 等）
        response = client.chat.completions.create(
            model=settings.MODEL_NAME,  # 模型名称（从 .env 读取）
            messages=messages,  # 完整的对话历史
            temperature=0.7,  # 创造性参数（0-1，0.7 较均衡）
            max_tokens=800,  # 最大生成 token 数（控制回答长度）
            timeout=60.0,  # 请求超时时间（秒）
        )
        
        # ========== 步骤 4：提取回答并进行安全过滤 ==========
        # 从 LLM 响应中提取文本内容
        # choices[0] 表示第一个生成结果（通常只有一个）
        reply = response.choices[0].message.content
        
        # 应用安全过滤（双保险机制的第二层）
        # 检查是否包含敏感词汇，如有则追加安全提醒
        reply = filter_unsafe_content(reply)
        
        # 返回最终结果
        return ChatResponse(reply=reply)
    
    except Exception as e:
        # 异常处理：捕获所有可能的错误
        # 常见错误类型：
        # 1. API 连接失败（网络问题、API Key 错误、超时等）
        # 2. API 费用不足
        # 3. Token 数超限
        # 4. 模型不存在或不可用
        # 返回 500 错误给客户端，并附带错误信息
        raise HTTPException(status_code=500, detail=f"AI 服务异常: {str(e)}")


# ============== Phase 3 新增模块注册 ==============
# 导入并注册新模块（档案管理、对话历史管理）
# 这些模块独立于主代码，保持 main.py 简洁
from modules.profile import register_routes as register_profile
from modules.history import register_routes as register_history
from modules.adapter import register_routes as register_adapter

# 注册模块路由
register_profile(app)
register_history(app)
register_adapter(app)

# ============== 服务启动入口 ==============

if __name__ == "__main__":
    """
    直接运行此文件时的启动逻辑
    
    使用 Uvicorn 启动 FastAPI 应用：
    - host="0.0.0.0": 监听所有网络接口（允许外部访问）
    - port=8000: 监听 8000 端口
    - reload=True: 开发模式，代码修改后自动重启
    - reload_excludes: 排除测试文件，避免测试时触发重启
    
    访问方式：
    - API 文档：http://localhost:8000/docs
    - API 接口：http://localhost:8000/chat
    
    生产环境建议：
    - 关闭 reload（提高性能）
    - 使用进程管理器（如 systemd, supervisor）
    - 配置 HTTPS
    - 限制 CORS 为具体域名
    """
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_excludes=["test_*.py", "*_test.py", "tests/*"]  # 排除测试文件
    )
