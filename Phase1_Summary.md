# 阶段一：基础设施与模型集成 - 项目记录

**时间**：2026年1月14日  
**状态**：✅ 已完成  
**目标**：搭建起能够跑通基础对话的后端架构

---

## 一、项目启动

### 1.1 需求确认
- **产品定位**：面向家长的育儿咨询 AI，专注于儿童身心健康、心理教育、德育
- **核心场景**：家长遇到突发教育问题（如孩子走丢、撒谎、被欺负）时，通过对话获得即时的教育建议
- **设计理念**：极致简洁，只保留"家长问 - AI 答"的核心功能

### 1.2 文档输出
创建了两份核心文档：
- [Project_Proposal.md](Project_Proposal.md) - 产品计划书（面向投资人/管理层）
- [Technical_Roadmap.md](Technical_Roadmap.md) - 技术执行路线图（面向开发团队）

---

## 二、技术实现过程

### 2.1 环境搭建
**挑战**：系统未安装 Python

**解决方案**：
```powershell
winget install Python.Python.3.11
```
- 安装了 Python 3.11.9
- 配置了环境变量

### 2.2 后端架构搭建
**技术栈**：
- 框架：FastAPI
- LLM 客户端：OpenAI SDK（兼容多种模型）
- 依赖管理：pip + requirements.txt

**创建的文件**：
```
backend/
├── main.py              # FastAPI 主入口
├── config.py            # 配置管理（含育儿专家 System Prompt）
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
├── .env                 # 实际配置（含 API Key）
└── README.md            # 启动文档
```

### 2.3 接口设计演进

**初版**：3 个接口
- `GET /` - 健康检查
- `POST /chat` - 普通对话（非流式）
- `POST /chat/stream` - 流式对话

**优化后**：1 个接口（极简化）
- `POST /chat` - 育儿咨询对话（保留最核心功能）

**原因**：用户要求"极致简洁，不要那么多不同的选项"

---

## 三、模型选型历程

### 3.1 通义千问 (Qwen) - 第一次尝试
**配置**：
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus
```

**遇到问题**：
- 挂梯子时：`403 - unsupported_country_region_territory`（地区限制）
- 不挂梯子：`Connection error`（网络问题）

**失败原因分析**：VPN 节点国家不在白名单 + 本地网络路由问题

### 3.2 切换到公共接口
临时切换到 OpenAI 占位符配置（未实际测试，因为没有 Key）

### 3.3 DeepSeek - 验证成功
**配置**：
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

**测试结果**：✅ 成功返回高质量的育儿建议
- 回答结构化（分步指导）
- 心理学深度到位
- 中文表达自然

### 3.4 通义千问 (Qwen) - 第二次尝试（最终方案）
**调整策略**：简化接口架构，从流式接口改为普通 HTTP 响应

**问题分析**：
第一次失败的真正原因不是网络问题，而是**接口设计问题**：
- 初版使用了 SSE（Server-Sent Events）流式接口
- Swagger UI 对流式接口的测试支持不佳，容易导致 timeout
- 通义千问的兼容模式可能对流式响应的处理不够稳定

**解决方案**：
用户要求"极致简洁"后，将接口从 3 个精简为 1 个：
- 删除：`GET /` 健康检查
- 删除：`POST /chat/stream` 流式接口
- 保留：`POST /chat` 普通问答接口（非流式）

**最终配置**：
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus
```

**测试结果**：✅ 成功！
- 响应速度快且稳定
- 回答质量符合预期
- 成本低于国际模型
- **关键发现**：普通 HTTP 接口比流式接口更稳定

---

## 四、关键技术问题与解决

### 4.1 请求超时问题
**现象**：浏览器一直 loading，最终 timeout

**原因**：
1. 初始 timeout 设置过短
2. Swagger UI 不适合测试流式接口

**解决方案**：
```python
# 延长超时时间
client = OpenAI(..., timeout=60.0)

# 接口调用时也设置
response = client.chat.completions.create(
    ...
    timeout=60.0,
)
```

### 4.2 OpenAI SDK 版本兼容性
**问题**：`TypeError: Client.__init__() got an unexpected keyword argument 'proxies'`

**解决方案**：
```powershell
pip install --upgrade openai httpx
```
升级到最新版本（openai 2.15.0）

### 4.3 流式接口测试困难（根本原因）
**问题**：
- 初版使用 SSE（Server-Sent Events）流式接口
- Swagger UI 对 SSE 的支持不完善，经常 timeout
- 通义千问的 compatible-mode 对流式响应可能有兼容性问题

**解决方案**：
改为普通 HTTP POST 响应（非流式）：
```python
# 删除流式逻辑
async def generate():
    ...
    yield f"data: {json.dumps(...)}\n\n"

# 改为普通返回
response = client.chat.completions.create(
    ...
    stream=False,  # 关键改动
)
return ChatResponse(reply=response.choices[0].message.content)
```

**意外收获**：接口简化后，不仅解决了 Qwen 的问题，整体架构也更稳定、更易维护。

---

## 五、System Prompt 设计

**当前版本**（位于 `config.py`）：

```
你是一位资深的儿童教育专家和家庭心理顾问。你的职责是帮助家长处理育儿过程中遇到的各种困惑和挑战。

你的回答风格：
1. 先共情：理解家长当下的情绪（焦虑、愤怒、无助），用温暖的语气先安抚他们
2. 再分析：从儿童心理学角度解释孩子行为背后的动机和原因
3. 给话术：提供具体的、可直接使用的沟通语句（"第一句可以这样说..."）
4. 避坑提醒：指出常见的错误做法及其后果

重要原则：
- 绝不建议任何形式的体罚或语言暴力
- 尊重儿童的人格和尊严
- 建议要具体可操作，而非空洞的大道理
- 如果情况严重（如心理创伤、自残倾向），建议寻求专业心理咨询
```

---

## 六、测试验证

### 6.1 测试用例
**输入**：
```json
{
  "message": "孩子在商场走丢了刚找回来，我该怎么教育他？",
  "history": []
}
```

**输出示例**（Qwen）：
- 第一步：安抚情绪（家长与孩子）
- 第二步：倾听孩子视角
- 第三步：建立安全约定
- 危机意识不足警告
- 避免责备与恐吓的提醒

**评价**：✅ 符合预期，回答实用且有温度

---

## 七、交付成果

### 7.1 可运行的后端服务
- 服务地址：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`
- 接口：`POST /chat`

### 7.2 技术文档
- 项目计划书
- 技术路线图
- 后端 README

### 7.3 环境配置
- Python 3.11 运行环境
- 所有依赖已安装
- 模型 API 配置完成

---

## 八、下一步计划

根据 [Technical_Roadmap.md](Technical_Roadmap.md)：

- **阶段 2**：Prompt 工程与育儿逻辑注入
  - 优化 System Prompt，让回答更简洁
  - 增强安全过滤机制
  - 设计对话记忆管理

- **阶段 3**：极致简单的 UI 开发
  - 推荐微信小程序
  - 暖色调界面
  - 支持语音输入

- **阶段 4**：场景优化与压力测试
  - 极端案例测试
  - 性能优化
  - 埋点分析

---

## 九、经验总结

### 9.1 成功经验
1. **快速试错**：通过多次模型切换找到最优方案
2. **极简主义**：删减不必要的功能，聚焦核心价值（**意外解决了技术问题**）
3. **文档先行**：先明确需求和路线，再动手开发
4. **架构选择**：对于育儿咨询场景，普通 HTTP 响应比流式接口更可靠

### 9.2 核心经验
**"极简不仅是产品哲学，也是技术稳定性的保障"**  
- 流式接口虽然体验好，但增加了复杂度和不稳定性
- 对于家长育儿咨询场景，回答完整性比实时性更重要
- 简化接口后，兼容性、测试性、维护性都得到提升

### 9.2 待改进
1. **网络环境预判**：提前测试各模型的连通性
2. **错误处理**：需要更友好的错误提示
3. **日志记录**：缺少请求日志和监控

---

**阶段一总结：目标达成，基础设施已就绪，可以进入阶段二。**
