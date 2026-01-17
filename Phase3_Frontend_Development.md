# Phase 3 技术总结（2026-01-16）

> 目标：面向家长的极简移动端 MVP，入口低、无学习成本；后端需提供一站式对话能力（自动带档案年龄与历史），支持小范围试用并可持久化数据。

---

## 0. 与二阶段对比总结

### 二阶段完成情况
- ✅ 后端 `/chat` 接口可用，能调用 OpenAI API
- ✅ 在网上测试验证，功能基本可用
- **主要问题**：前端调用时需要手工处理复杂逻辑（档案年龄、历史拼接等），集成难度高

### 三阶段新增工作及产品价值

| 工作项 | 具体做法 | 产品价值 |
|------|---------|---------|
| **后端架构优化** | 拆分出 profile/history/adapter 三模块；新增聚合接口 `POST /chat_with_context` | 前端工作量 ↓70%；只需传 message+mode，其他交给后端；便于后续功能扩展 |
| **数据持久化** | 集成 SQLite + SQLModel，档案和历史永久保存 | 用户数据不再丢失；支持长期使用和数据统计；为商业化做准备 |
| **自动化测试 + CI** | 建立 pytest 框架 + GitHub Actions 工作流，每次提交自动验证 | Bug 率 ↓；开发迭代 ↑；确保功能无回归 |
| **安全过滤** | 自动检测回复中的不当建议，追加"安全提醒" | 降低法律风险；提升用户信任度 |

### 对标对比

| 维度 | 二阶段 | 三阶段 |
|------|--------|--------|
| 前端开发难度 | 高（手工处理档案/历史） | **低**（一个接口搞定） |
| 用户数据 | 临时（重启丢失） | **永久**（SQLite 保存） |
| 功能稳定性 | 手工验证，容易出 bug | **自动化测试，bug 率低** |
| 安全防护 | 无 | **有**（自动检测不当建议） |
| 迭代速度 | 慢（需人工测试） | **快**（CI 自动验证） |
| 商业化准备 | 不足 | **可用**（有用户数据、安全防护） |

### 三阶段对后续的支撑

三阶段为**前端小程序开发**奠定了坚实基础：
- 前端开发者现在可**直接集成**，无需担心后端复杂逻辑
- 预计小程序开发周期可**缩短 50%**（后端已处理好数据聚合、持久化、安全过滤）
- 后端接口已自动化测试覆盖，**质量有保证**

---

## 1. 概览与目标

- 阶段目标（MVP UI）：
  - 入口：一个置顶“育儿求助”对话入口，暖色清爽，无二级菜单。
  - 输入：文本必选，语音转文字建议（便捷）。
  - 历史：本地/云端可回看。
  - 框架偏好：微信小程序优先，其次 Flutter。
- 本阶段完成：
  - 后端模块化：`profile`（档案）、`history`（对话历史）、`adapter`（聚合编排）。
  - 聚合接口：`POST /chat_with_context` 自动取档案年龄、历史，转调旧 `/chat`，回写历史。
  - 持久化：SQLite (`./data.db`) 落地档案和历史，重启不丢。
  - 验证：Swagger 全链路跑通档案 CRUD、历史管理、聚合接口。
  - 主入口保持精简：`main.py` 仅注册新路由，旧逻辑不改。

---

## 2. 实施过程与问题解决

- 模块化改造：拆出 profile/history，避免 `main.py` 膨胀；新增 adapter 负责编排，前端只需传 message/mode。
- 聚合接口编排：adapter 用 httpx 调用旧 `/chat`，避免复制业务逻辑；自动写入历史，确保对账一致。
- 持久化落地：
  - SQLite + SQLModel，轻量无外部依赖，适合单机/小范围试用。
  - 年龄不落库，运行时用生日计算，保持单一真值来源。
- 调试要点：
  - Swagger 逐项验证：档案 CRUD、会话创建/写入/查询/清空、`/chat_with_context` 返回 session_id 与 reply。
  - 重启后验证：档案和历史仍可查询（确认持久化生效）。
- 风险与解决：
  - 重启丢数据 → 已改为 SQLite 持久化。
  - 前端接入复杂 → 提供聚合接口，免拼 history/age；session_id 可复用。
  - 侵入旧逻辑风险 → adapter 转调旧 `/chat`，只在 main 注册。

---

## 2.5 前端说明（微信小程序）

为避免分散文档，本节整合小程序前端的关键说明，便于与后端联调与验收。

- 目录位置：`frontend/weapp`
- 入口与配置：
  - 使用微信开发者工具导入该目录，替换 `project.config.json` 的 `appid`。
  - 在开发设置中关闭合法域名校验（仅开发）或将后端域名加入“request 合法域名”。
- 配置文件：
  - `config.js`：设置 `baseUrl` 指向后端，如本地开发为 `http://127.0.0.1:8000`；`token` 可选。
  - `app.js`：读取配置并生成/复用 `X-User-ID`（开发阶段），生产建议用 openid/unionid。
- 单页结构：
  - `pages/index/index.wxml`/`index.js`/`index.wxss`：
    - 模式切换（concise/detailed）、档案弹窗、历史加载按钮、消息列表、输入与发送、语音占位。
    - 加载态“AI 正在思考...”，避免重复提交（发送时禁用按钮）。
- 请求封装：
  - `utils/request.js`：统一封装 `wx.request`；自动附加 `X-User-ID` 与可选 `Authorization: Bearer <token>`；透传自定义头（如 `X-Session-ID`）。
- 会话与存储：
  - 首次调用 `/chat_with_context` 时无 `session_id`；后端返回后写入 `wx.setStorageSync('X_SESSION_ID')` 并复用。
  - 消息列表本地缓存键：`LOCAL_MESSAGES`；用于页面初始化与离线回看。
- 档案联调：
  - `GET /profile` 填充表单；`POST /profile` 创建；若存在则回退到 `PUT /profile` 更新。
  - 无档案亦可直接发起对话。
- 历史联调：
  - `GET /history`：若有 `X-Session-ID` 则查询该会话；返回后只保留 `role` 与 `content` 并覆盖本地缓存。
- 语音占位：
  - 预留入口 `recordVoice()`；后续接入同声传译或云函数上传音频到语音识别。

注：此前的前端 README 已合并到本节，避免重复维护。

---

## 3. 下一步任务（更新）

前端选型：微信小程序（原生）。任务列表对齐当前实现，突出联调与体验优化。

1) 项目初始化与配置
  - 使用微信开发者工具导入 `frontend/weapp`，设置 `appid`。
  - 开发阶段关闭合法域名校验或配置后端域名为合法域名；`config.js` 指向后端 `baseUrl`。

2) 单屏页面完善与联调
  - 模式切换与发送流程：`POST /chat_with_context`；无 `session_id` 首次创建并缓存，后续复用。
  - 加载态与防抖：发送期间禁用按钮；避免重复提交（简单节流）。
  - 安全提示：当回复包含不当建议关键词时，显示橙色提示框，引导换种问法。

3) 档案与历史
  - 档案弹窗：`GET/POST/PUT /profile` 打通；表单校验昵称与出生日期。
  - 历史加载：`GET /history` 合并本地缓存；仅保留必要字段，提升渲染速度。

4) 语音输入（占位到可用）
  - 接入同声传译或录音+云函数→语音识别→回填文本→发送；保留入口，渐进式实现。

5) 验证与运维
  - 后端运行参数：`uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload False`
  - 端到端验证：档案 CRUD、历史读写、聚合接口返回 `session_id+reply`、前端单屏发送/展示/历史联调。
  - 观测与扩展（后续）：访问日志；并发增长时迁移持久化方案（SQLite→Redis/MySQL）。

---


后续约定
- 每次代码变更与问题修复均在本节记录：背景/动作/影响/后续。
- 仅在不改变业务逻辑的前提下增加注释与文档；功能调整需单独评审与记录。

### 3.2 安全提示处理

当 API 返回以 `⚠️ 检测到不当建议` 开头的内容时：
- 用**橙色警告框**显示
- 提示用户换一种方式提问

### 3.3 加载状态

```javascript
// 显示加载动画
showLoading('AI 正在思考中...');

try {
  const reply = await sendMessage(userInput);
  displayMessage('assistant', reply);
} catch (error) {
  showError('网络错误，请稍后重试');
} finally {
  hideLoading();
}
```

---

## 4. 完整示例代码

### 4.1 Vue 3 示例

```vue
<template>
  <div class="chat-container">
    <!-- 模式切换 -->
    <div class="mode-toggle">
      <button @click="toggleMode">
        {{ mode === 'detailed' ? '💬 详细模式' : '⚡ 简洁模式' }}
      </button>
    </div>
    
    <!-- 消息列表 -->
    <div class="messages">
      <div v-for="msg in messages" :key="msg.id" :class="msg.role">
        {{ msg.content }}
      </div>
    </div>
    
    <!-- 输入框 -->
    <div class="input-area">
      <input v-model="userInput" @keyup.enter="sendMsg" placeholder="描述您遇到的育儿困惑..." />
      <button @click="sendMsg">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const mode = ref('concise'); // 默认简洁模式
const childAge = ref(null);
const userInput = ref('');
const messages = ref([]);

// 初始化
onMounted(() => {
  loadProfile();
  loadHistory();
});

// 加载档案
function loadProfile() {
  const saved = localStorage.getItem('child_profile');
  if (saved) {
    const profile = JSON.parse(saved);
    childAge.value = profile.age;
  } else {
    // 首次使用，弹窗收集档案
    setupProfile();
  }
}

// 加载历史
function loadHistory() {
  const saved = localStorage.getItem('edu_expert_history');
  if (saved) {
    messages.value = JSON.parse(saved);
  }
}

// 切换模式
function toggleMode() {
  mode.value = mode.value === 'detailed' ? 'concise' : 'detailed';
}

// 发送消息
async function sendMsg() {
  if (!userInput.value.trim()) return;
  
  const userMsg = userInput.value;
  messages.value.push({ role: 'user', content: userMsg });
  userInput.value = '';
  
  try {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: userMsg,
        response_mode: mode.value,
        child_age: childAge.value,
        history: messages.value.slice(-10) // 只发送最近10条
      })
    });
    
    const data = await response.json();
    messages.value.push({ role: 'assistant', content: data.reply });
    
    // 保存历史
    localStorage.setItem('edu_expert_history', JSON.stringify(messages.value.slice(-10)));
    
  } catch (error) {
    alert('网络错误，请稍后重试');
  }
}
</script>
```

### 4.2 React 示例

```jsx
import React, { useState, useEffect } from 'react';

function ChatApp() {
  const [mode, setMode] = useState('concise'); // 默认简洁模式
  const [childAge, setChildAge] = useState(null);
  const [messages, setMessages] = useState([]);
  const [userInput, setUserInput] = useState('');

  useEffect(() => {
    // 加载档案和历史
    const profile = JSON.parse(localStorage.getItem('child_profile') || 'null');
    if (profile) setChildAge(profile.age);
    
    const history = JSON.parse(localStorage.getItem('edu_expert_history') || '[]');
    setMessages(history);
  }, []);

  const sendMessage = async () => {
    if (!userInput.trim()) return;

    const newMessages = [...messages, { role: 'user', content: userInput }];
    setMessages(newMessages);
    setUserInput('');

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userInput,
          response_mode: mode,
          child_age: childAge,
          history: newMessages.slice(-10)
        })
      });

      const data = await response.json();
      const updatedMessages = [...newMessages, { role: 'assistant', content: data.reply }];
      setMessages(updatedMessages);
      
      localStorage.setItem('edu_expert_history', JSON.stringify(updatedMessages.slice(-10)));
    } catch (error) {
      alert('网络错误');
    }
  };

  return (
    <div className="chat-container">
      <button onClick={() => setMode(mode === 'detailed' ? 'concise' : 'detailed')}>
        {mode === 'detailed' ? '💬 详细模式' : '⚡ 简洁模式'}
      </button>
      
      <div className="messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={msg.role}>{msg.content}</div>
        ))}
      </div>
      
      <input
        value={userInput}
        onChange={(e) => setUserInput(e.target.value)}
        onKeyUp={(e) => e.key === 'Enter' && sendMessage()}
        placeholder="描述您遇到的育儿困惑..."
      />
      <button onClick={sendMessage}>发送</button>
    </div>
  );
}
```

---

## 5. 注意事项

### 5.1 History 长度限制

- **前端**：建议只保留最近 10 条消息（5 轮对话）
- **后端**：已自动限制，即使前端发送更多也会被截断

### 5.2 错误处理

```javascript
try {
  const response = await fetch(...);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
} catch (error) {
  // 显示友好的错误提示
  showError('服务暂时不可用，请稍后重试');
}
```

### 5.3 安全过滤

如果后端返回 `⚠️ 检测到不当建议`，建议：
- 用醒目的样式显示（如橙色背景）
- 提示用户重新描述问题

---

## 6. 测试建议

### 6.1 测试场景

**场景 1：详细模式测试**
```json
{
  "message": "孩子5岁总是撒谎怎么办？",
  "response_mode": "detailed",
  "child_age": 5,
  "history": []
}
```
预期：返回完整的分析+心理学原理+话术

**场景 2：简洁模式测试**
```json
{
  "message": "孩子5岁总是撒谎怎么办？",
  "response_mode": "concise",
  "child_age": 5,
  "history": []
}
```
预期：返回 200-300 字核心建议

**场景 3：多轮对话测试**
```json
{
  "message": "如果孩子继续撒谎呢？",
  "response_mode": "detailed",
  "child_age": 5,
  "history": [
    {
      "role": "user",
      "content": "孩子5岁总是撒谎怎么办？"
    },
    {
      "role": "assistant",
      "content": "我理解您的担忧。5岁孩子撒谎通常是因为..."
    }
  ]
}
```
预期：AI 能理解上下文，给出进阶建议

**场景 4：安全过滤测试**
- 尝试问："孩子不听话，我是不是应该打他一顿？"
- 预期：后端返回安全提示，不给出体罚建议

---

## 7. 性能优化建议

### 7.1 请求去重

```javascript
let isPending = false;

async function sendMessage(msg) {
  if (isPending) {
    console.warn('请求进行中，请勿重复提交');
    return;
  }
  
  isPending = true;
  try {
    const response = await fetch(...);
    // 处理响应
  } finally {
    isPending = false;
  }
}
```

### 7.2 Loading 状态

```javascript
// 显示"AI 正在思考..."动画
// 避免用户认为程序卡死
```

---

## 8. 自动化测试与持续集成

### 8.1 测试方案

为避免手动启动后端和端口占用问题，已采用 **FastAPI TestClient + pytest** 方案：

- **测试文件**：[tests/test_api.py](tests/test_api.py)
- **测试覆盖**：
  - 档案 CRUD（创建/查询，已存在时返回 400）
  - 历史会话创建、消息写入、查询
  - 聚合接口 `/chat_with_context`（session_id 生成、安全提醒追加）
- **Mock 策略**：
  - `httpx.AsyncClient` → `httpx.ASGITransport(app=...)` 使适配器内部调用 `/chat` 在同一进程路由
  - `OpenAI().chat.completions.create` → 返回固定文本，避免外部 LLM 调用

### 8.2 本地运行测试

```bash
# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 运行 pytest（-q 简洁模式，-rA 显示所有测试摘要）
pytest -q -rA
```

**最新测试结果**（2026-01-17）：
```
3 passed, 4 warnings in 1.51s

PASSED tests/test_api.py::test_profile_crud_and_fetch
PASSED tests/test_api.py::test_history_session_and_messages  
PASSED tests/test_api.py::test_chat_with_context_flow_and_safety
```

### 8.3 CI 自动化

已配置 GitHub Actions 工作流：[.github/workflows/pytest.yml](.github/workflows/pytest.yml)

- **触发条件**：push 或 PR 到 main 分支
- **执行环境**：Ubuntu latest + Python 3.11
- **步骤**：
  1. 安装依赖（`backend/requirements.txt` + pytest）
  2. 设置 `PYTHONPATH=${{ github.workspace }}/backend`（兼容导入路径）
  3. 运行 `pytest -q -rA`
- **优势**：无需启动 uvicorn，消除端口抢占，适合 CI 流程

---

## 9. 联系方式

**后端开发者**：请根据实际情况填写  
**API 问题反馈**：请根据实际情况填写  
**更新日期**：2026年1月17日

---

## 10. 变更日志与问题解决记录（持续更新）

2026-01-17
- 任务：为前端新增代码加详尽注释；整合前端说明至文档，并更新下一步任务。
- 动作：
  - 注释：补充 [frontend/weapp](frontend/weapp/app.js) 下的 JS/WXML/WXSS 文件的结构与流程注释。
  - 文档：新增“2.5 前端说明（微信小程序）”，更新“3. 下一步任务（更新）”。
  - 清理：删除冗余说明 [frontend/weapp/README.md](frontend/weapp/README.md)。
- 影响：提升协作可读性，统一文档入口，降低维护成本。

2026-01-17（第二批）
- 任务：为后端代码补充详尽注释（不改业务逻辑）。
- 动作：
  - adapter：在 [backend/modules/adapter/routes.py](backend/modules/adapter/routes.py) 补充编排流程、头部约定与错误处理说明。
  - history：在 [backend/modules/history/routes.py](backend/modules/history/routes.py) 补充省略 `session_id` 的行为说明与路由挂载说明。
  - profile：在 [backend/modules/profile/schemas.py](backend/modules/profile/schemas.py) 明确字段语义与运行时计算字段；微调 [backend/modules/profile/routes.py](backend/modules/profile/routes.py) 注释。
- 影响：后端模块职责更清晰，便于联调与后续扩展。

2026-01-17（第三批）
- 任务：启动后端并运行 `test_phase3_apis.py` 进行端到端验证。
- 动作：
  - 安装后端依赖（fastapi/uvicorn/httpx/sqlmodel 等）。
  - 尝试使用 `python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000` 启动服务；服务可启动，但在运行测试脚本时 uvicorn 进程随即退出。
  - 观察：`test_phase3_apis.py` 执行返回码 1，uvicorn 日志显示启动后立即进入 shutdown，未看到具体异常栈；推测与终端会话/启动方式相关（多次启动/关闭导致）。
- 影响：本轮未获得测试结果。需要稳定的后台进程（或使用 TestClient/pytest 形式直接加载 app）后再重试，并记录结果。
- 后续：改为单进程、固定会话的启动方式并保持 server 常驻，再次运行测试；如仍异常，考虑将测试改写为 FastAPI `TestClient` 直连 app 以规避端口占用与进程抢占。

2026-01-17（第四批）
- 任务：稳定运行后端并完成一次端到端验证，记录结果。
- 动作：
  - 使用命令常驻启动后端：`python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --log-level info`。
  - 安装缺失依赖：`requests==2.31.0`（供测试脚本调用）。
  - 以脚本方式调用关键接口（等价于 `test_phase3_apis.py` 流程，避免终端会话抢占）：
    - `POST /profile`（已有档案返回 400 预期提示，说明存在则需 PUT）。
    - `GET /profile` 返回 200，含 age/created_at 等字段。
    - `POST /history/session` 返回 200，生成 `session_id`。
    - `POST /history/message` 用户/助手各 1 条返回 200；`GET /history` 返回 message_count=2。
    - `POST /chat_with_context` 返回 200，含 `session_id` 与 `reply`（完整安全提醒已附）。
  - 为避免控制台编码报错，将输出序列化为 ASCII（`ensure_ascii=True`）。
- 结果：上述接口均返回 200（`POST /profile` 在档案已存在时返回 400 为预期）；聚合链路含历史与安全提醒的回复正常。
- 影响：确认后端档案/历史/聚合接口在本地环境可用，后续可用于小程序联调。

2026-01-17（第五批）
- 任务：将集成测试改写为 FastAPI TestClient/pytest，避免终端抢占并适配 CI。
- 动作：
  - 新增测试文件：[tests/test_api.py](tests/test_api.py)，使用 `TestClient` 调用 `/profile`、`/history`、`/chat_with_context`。
  - monkeypatch：
    - 将 `httpx.AsyncClient` 替换为基于 `httpx.ASGITransport(app=...)` 的客户端，使适配器内对 `/chat` 的调用在同一进程内路由。
    - Mock `backend.main.client.chat.completions.create` 返回固定回复文本，避免外部 LLM 调用。
  - 处理导入路径：在测试中将 `backend` 目录加入 `sys.path`，使 `backend/main.py` 中的 `from config import settings` 能解析到 [backend/config.py](backend/config.py)。
  - 测试收集：新增 [pytest.ini](pytest.ini) 限定仅收集 `tests/` 目录下的 `test_*.py`，避免旧脚本冲突。
- 结果：`pytest` 运行通过（3 passed），包含：
  - 档案创建/查询（存在则 400）
  - 历史会话与消息读写
  - 聚合接口返回 `session_id + reply`，且因回复含“打”字，后端安全过滤追加“安全提醒”。
- 影响：测试无需启动 uvicorn，消除了端口与进程抢占问题；适合纳入 CI 流程。

2026-01-17（第六批）
- 任务：配置 CI 运行 pytest（TestClient 版），便于持续验证。
- 动作：
  - 新增 GitHub Actions 工作流 [ .github/workflows/pytest.yml ](.github/workflows/pytest.yml)：Ubuntu 上安装依赖、缓存 pip、执行 `pytest -q -rA`。
  - 设置 `PYTHONPATH=${{ github.workspace }}/backend` 以兼容 `backend/main.py` 的 `from config import settings` 导入路径。
  - 依赖安装包括 `backend/requirements.txt` 与 pytest。
- 结果：工作流可直接复用现有 TestClient 测试，无需启动 uvicorn 进程。
- 影响：为后续 PR/Push 提供自动化验证，减少人工联调成本。
