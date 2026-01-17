# 教育专家 AI - 后端服务

## 快速启动

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量
复制 `.env.example` 为 `.env`，并填入你的 API Key：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
OPENAI_API_KEY=你的API密钥
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
```

如果使用 DeepSeek：
```
OPENAI_API_KEY=你的DeepSeek密钥
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
```

### 3. 启动服务
```bash
python main.py
```

服务将运行在 `http://localhost:8000`

## API 接口

### 健康检查
```
GET /
```

### 普通对话（非流式）
```
POST /chat
Content-Type: application/json

{
    "message": "孩子刚才在商场走丢了，找回来后我该怎么教育他？",
    "history": []
}
```

### 流式对话（推荐）
```
POST /chat/stream
Content-Type: application/json

{
    "message": "孩子总是撒谎，我应该怎么处理？",
    "history": [
        {"role": "user", "content": "之前的问题..."},
        {"role": "assistant", "content": "之前的回答..."}
    ]
}
```

响应为 SSE 格式，逐块返回 AI 的回复。

## 项目结构
```
backend/
├── main.py           # FastAPI 主入口
├── config.py         # 配置管理
├── requirements.txt  # Python 依赖
├── .env.example      # 环境变量示例
└── README.md         # 本文档
```
