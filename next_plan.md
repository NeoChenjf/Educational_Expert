# 下一步协作提示（交接给下一个助手）

请阅读本文件后，继续当前工作流。上下文已简述，优先保持精简、可执行。

## 项目快照
- 后端：FastAPI，模块 profile（档案）、history（历史）、adapter（聚合）。聚合接口 `POST /chat_with_context` 自动带档案年龄与历史，转调旧 `/chat`，并写历史。
- 持久化：SQLite `./data.db`（SQLModel），年龄运行时计算（不入库）。
- 测试：新增 `tests/test_api.py` 基于 FastAPI `TestClient` + `httpx.ASGITransport` + OpenAI mock，`pytest` 本地通过（3 passed）。
- CI：GitHub Actions `.github/workflows/pytest.yml` 运行 pytest，无需启动 uvicorn。
- 前端：微信小程序（原生），说明集中在 Phase3 文档的“2.5 前端说明”。

## 今日变更
- Phase3_Frontend_Development.md：已恢复并追加“9. 变更日志与问题解决记录”，保持章节顺序；第3章待办锁定小程序方案。
- 测试与 CI：测试改为 `TestClient`/pytest；新增 GitHub Actions 工作流跑 pytest；旧 `test_phase3_apis.py` 已替换为 `tests/test_api.py`。

## 待继续的工作（优先级）
1) 小程序联调：用微信开发者工具导入 `frontend/weapp`，配置 AppID 与后端合法域名，`config.js` 指向后端。
2) 页面完善：单屏 `pages/index` 补齐模式切换/发送/加载态/安全提示（橙色警告框）。
3) 接口接入：
   - `POST /chat_with_context`：首次不带 session_id，返回后写 `wx.setStorageSync`，后续复用；请求头附 `X-User-ID`（app.js 已生成）。
   - 鉴权：如需 token，从配置注入 `Authorization: Bearer <token>`。
4) 档案与历史：
   - 档案表单：`GET/POST/PUT /profile`，无档案也可直接对话；本地缓存一份。
   - 历史：启动时读本地缓存，再调 `/history`（含 session_id）覆盖本地缓存。
5) 语音：保留入口，接入同声传译或云函数上传音频→语音识别→填充输入框。
6) 体验与测试：节流防抖；“AI 正在思考...”加载态；复用现有 pytest 用例，必要时新增前后端联调脚本（可参考现有 mock 方式）。
7) 运行与验证：
   - 后端：`uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload False`
   - 验证：档案持久化、`/chat_with_context` 返回 session_id+reply、历史自动写入可查；前端单屏发送/展示/历史/安全提示链路走通。

## 关键文件位置
- 文档：Phase3_Frontend_Development.md（含前端说明、变更日志）。
- 后端入口：backend/main.py
- 模块：backend/modules/profile/*, history/*, adapter/*
- 测试：tests/test_api.py（TestClient 版）；CI：.github/workflows/pytest.yml

## 注意事项
- 遵循现有持久化与接口，不要修改 `/chat_with_context` 行为；安全提醒逻辑已在适配器中追加。
- 保持 UI 极简；优先完成可运行 MVP，再做加分项（限流/指标）。
- 前端示例已合并至 Phase3 文档，可对照改写成小程序 API（wx.request）。

（完）
