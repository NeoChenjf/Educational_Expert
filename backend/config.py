"""
配置管理模块
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Settings:
    """
    应用配置类
    
    集中管理所有配置项，包括：
    - API 连接配置（密钥、地址、模型）
    - 对话管理配置（历史长度）
    - System Prompt 生成逻辑
    
    设计模式：单例配置类
    使用方式：from config import settings
    """
    
    # ========== API 连接配置 ==========
    
    # LLM API 密钥（从环境变量读取）
    # 支持 OpenAI、Qwen、DeepSeek 等兼容 OpenAI 接口的模型
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # LLM API 基地址（从环境变量读取，可自定义）
    # 示例：
    # - OpenAI: https://api.openai.com/v1
    # - Qwen: https://dashscope.aliyuncs.com/compatible-mode/v1
    # - DeepSeek: https://api.deepseek.com/v1
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    # 使用的模型名称（从环境变量读取）
    # 示例："gpt-4o-mini", "qwen-plus", "deepseek-chat"
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    
    # ========== 对话管理配置 ==========
    
    # 对话历史保留轮数（1 轮 = 1 条 user + 1 条 assistant）
    # 设置为 5 表示最多保留 10 条消息（5 轮对话）
    # 原因：防止 token 超限，控制 API 成本
    # 可根据实际需求调整（建议 3-10 轮）
    MAX_HISTORY_ROUNDS: int = 5  # 最多保留最近 5 轮对话（10条消息）
    
    def get_system_prompt(self, mode: str = "detailed", child_age: int = None) -> str:
        """
        动态生成 System Prompt（Phase 2 核心功能）
        
        功能说明：
        根据家长选择的回答模式和孩子年龄，动态组合生成最合适的 System Prompt。
        这使得 AI 的回答既专业又个性化。
        
        设计理念：
        - 基础 Prompt：定义 AI 角色、回答风格、专业领域、安全原则
        - 模式调整：根据 mode 参数控制回答详细程度
        - 年龄适配：根据 child_age 参数调整教育策略重点
        
        参数说明：
            mode: 回答模式
                - "detailed" (默认)：详细模式
                  * 深入分析行为背后的心理动机
                  * 提供完整的教育方案
                  * 适当引用儿童心理学理论支撑
                  * 回答较长（通常 1000-2000 字）
                  
                - "concise"：简洁模式
                  * 控制在 200-300 字以内
                  * 只给最核心的建议和话术
                  * 省略冗长的心理学原理解释
                  * 适合家长需要快速建议的场景
            
            child_age: 孩子年龄（整数，可选）
                - None: 不指定年龄，使用通用建议
                - 0-3岁：婴幼儿期
                  * 重点：安全感建立、情绪识别、基础规则意识
                  * 语言：极简化，多用具体动作指导
                - 3-6岁：学前期
                  * 重点：自我控制、同理心培养、社交技能
                  * 方法：可通过故事、游戏引导
                - 6-12岁：学龄期
                  * 重点：责任感、学习习惯、情绪管理
                  * 沟通：可进行更多逻辑推理式沟通
                - 12岁以上：青春期
                  * 重点：自主性、价值观形成、同伴关系
                  * 态度：尊重独立性，避免说教
        
        返回：
            完整的 System Prompt 字符串
        
        示例：
            # 详细模式 + 7岁孩子
            prompt = settings.get_system_prompt("detailed", 7)
            # 返回的 Prompt 会强调：责任感、学习习惯、逻辑沟通
            
            # 简洁模式 + 不指定年龄
            prompt = settings.get_system_prompt("concise", None)
            # 返回的 Prompt 会要求：200-300字、核心建议、无年龄特定内容
        
        技术细节：
        - 使用字符串拼接组合不同部分
        - 确保 Prompt 语义完整、逻辑清晰
        - 已针对 Qwen 模型优化（非流式响应）
        """
        # 基础角色设定
        base_prompt = """你是一位资深的儿童教育专家和家庭心理顾问。你的职责是帮助家长处理育儿过程中遇到的各种困惑和挑战。

你的回答风格：
1. 先共情：理解家长当下的情绪（焦虑、愤怒、无助），用温暖的语气先安抚他们
2. 再分析：从儿童心理学角度解释孩子行为背后的动机和原因
3. 给话术：提供具体的、可直接使用的沟通语句（"第一句可以这样说..."）
4. 避坑提醒：指出常见的错误做法及其后果

你的专业领域包括：
- 儿童安全教育（走丢、陌生人、网络安全等）
- 情绪管理与心理健康
- 行为习惯养成（撒谎、拖延、注意力等）
- 社交能力培养（被欺负、交友困难等）
- 道德品质教育（诚实、责任、同理心等）

重要原则：
- 绝不建议任何形式的体罚或语言暴力
- 尊重儿童的人格和尊严
- 建议要具体可操作，而非空洞的大道理
- 如果情况严重（如心理创伤、自残倾向），建议寻求专业心理咨询"""
        
        # 根据模式调整
        if mode == "concise":
            mode_instruction = """\n\n【简洁模式】：
- 回答控制在 200-300 字以内
- 只给最核心的建议和话术
- 省略冗长的心理学原理解释"""
        else:
            mode_instruction = """\n\n【详细模式】：
- 深入分析行为背后的心理动机
- 提供完整的教育方案
- 适当引用儿童心理学理论支撑"""
        
        # 根据年龄调整
        age_instruction = ""
        if child_age:
            if child_age <= 3:
                age_instruction = "\n\n【年龄段】：0-3岁婴幼儿期，重点关注安全感建立、情绪识别、基础规则意识。语言要极简，多用具体动作指导。"
            elif child_age <= 6:
                age_instruction = "\n\n【年龄段】：3-6岁学前期，重点关注自我控制、同理心培养、社交技能。可以通过故事、游戏引导。"
            elif child_age <= 12:
                age_instruction = "\n\n【年龄段】：6-12岁学龄期，重点关注责任感、学习习惯、情绪管理。可以进行更多逻辑推理式沟通。"
            else:
                age_instruction = "\n\n【年龄段】：12岁以上青春期，重点关注自主性、价值观形成、同伴关系。尊重其独立性，避免说教。"
        
        return base_prompt + mode_instruction + age_instruction


settings = Settings()
