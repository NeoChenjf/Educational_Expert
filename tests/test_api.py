"""
FastAPI TestClient / pytest 端到端测试

目标：
- 避免真实网络端口与进程抢占，提升 CI 可用性
- 使用 TestClient 与 httpx.ASGITransport，将适配器内对 /chat 的调用在内存中路由到同一 app
- Mock OpenAI 客户端，避免外部依赖

注意：
- 测试默认会在当前工作目录创建/使用 `./data.db`（SQLite）。如需隔离，可在服务层支持自定义 DB URL。
- 不修改业务逻辑，只在测试中进行 monkeypatch。
"""

import json
import uuid
import httpx
import pytest
from fastapi.testclient import TestClient
import os
import sys

# 调整 PythonPath，使得 backend/main.py 中的 `from config import settings` 能解析到 backend/config.py
_BACKEND_PATH = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(_BACKEND_PATH))

# 导入应用（不启动 uvicorn）
import backend.main as main


@pytest.fixture(scope="session")
def app():
    """提供 FastAPI 应用实例（后端主应用）。"""
    return main.app


@pytest.fixture(autouse=True)
def patch_httpx_asyncclient(monkeypatch, app):
    """
    将适配器中的 httpx.AsyncClient 改为 ASGITransport 直连应用。
    - 保持接口一致（支持 async with），避免真实 HTTP 网络调用。
    """

    class AsyncClientPatched(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            transport = httpx.ASGITransport(app=app)
            # 使用统一的 base_url，适配绝对/相对路径
            super().__init__(transport=transport, base_url="http://testserver")

    monkeypatch.setattr("httpx.AsyncClient", AsyncClientPatched)


@pytest.fixture(autouse=True)
def patch_openai(monkeypatch):
    """
    Mock OpenAI 客户端的 chat.completions.create，返回可控的回复文本，
    以避免外部 API 依赖与费用。
    """

    class _Message:
        def __init__(self, content: str):
            self.content = content

    class _Choice:
        def __init__(self, content: str):
            self.message = _Message(content)

    class _Response:
        def __init__(self, content: str):
            self.choices = [_Choice(content)]

    def _fake_create(**kwargs):
        # 返回包含敏感词的示例文本，以测试后端安全提醒追加逻辑
        return _Response("建议不要打孩子，先共情再设边界。")

    monkeypatch.setattr(main.client.chat.completions, "create", _fake_create)


def _headers_for_user(user_id: str, session_id: str | None = None):
    headers = {"X-User-ID": user_id}
    if session_id:
        headers["X-Session-ID"] = session_id
    return headers


def test_profile_crud_and_fetch(app):
    client = TestClient(app)
    user_id = f"test_{uuid.uuid4().hex[:8]}"

    # 1) 创建档案（首次）
    resp_create = client.post(
        "/profile",
        headers=_headers_for_user(user_id),
        json={
            "nickname": "小明",
            "birth_date": "2017-05-20",
            "grade": "一年级",
            "notes": "性格活泼，喜欢画画",
        },
    )
    assert resp_create.status_code in (200, 400)
    # 若已存在则返回 400，继续验证查询

    # 2) 查询档案
    resp_get = client.get("/profile", headers=_headers_for_user(user_id))
    assert resp_get.status_code == 200
    data = resp_get.json()
    assert data["nickname"] == "小明"
    assert "age" in data


def test_history_session_and_messages(app):
    client = TestClient(app)
    user_id = f"test_{uuid.uuid4().hex[:8]}"

    # 1) 创建会话
    resp_sess = client.post("/history/session", headers=_headers_for_user(user_id))
    assert resp_sess.status_code == 200
    session_id = resp_sess.json()["session_id"]

    # 2) 添加用户消息
    resp_user = client.post(
        "/history/message",
        headers=_headers_for_user(user_id, session_id),
        json={"role": "user", "content": "孩子7岁不肯写作业怎么办？"},
    )
    assert resp_user.status_code == 200

    # 3) 添加 AI 回复
    resp_ai = client.post(
        "/history/message",
        headers=_headers_for_user(user_id, session_id),
        json={"role": "assistant", "content": "先共情，再给结构化建议"},
    )
    assert resp_ai.status_code == 200

    # 4) 查询历史
    resp_hist = client.get(
        "/history", headers=_headers_for_user(user_id, session_id)
    )
    assert resp_hist.status_code == 200
    hist = resp_hist.json()
    assert hist["message_count"] == 2
    assert hist["messages"][0]["role"] == "user"
    assert hist["messages"][1]["role"] == "assistant"


def test_chat_with_context_flow_and_safety(app):
    client = TestClient(app)
    user_id = f"test_{uuid.uuid4().hex[:8]}"

    # 首次无会话，聚合接口将自动创建/复用
    resp_chat = client.post(
        "/chat_with_context",
        headers=_headers_for_user(user_id),
        json={
            "message": "怎么激励孩子完成作业？",
            "response_mode": "concise",
            "history_limit": 5,
        },
    )
    assert resp_chat.status_code == 200
    data = resp_chat.json()
    assert "session_id" in data
    assert isinstance(data["reply"], str)

    # 因为我们 mock 的回复包含“打”字，
    # 后端安全过滤应追加“安全提醒”内容
    assert "安全提醒" in data["reply"]

    # 历史应包含双方消息各一条
    resp_hist = client.get(
        "/history", headers=_headers_for_user(user_id, data["session_id"])
    )
    assert resp_hist.status_code == 200
    hist = resp_hist.json()
    assert hist["message_count"] >= 2
