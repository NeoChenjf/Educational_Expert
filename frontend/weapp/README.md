# 教育专家助手 - 微信小程序前端

本目录为小程序前端（MVP 单页）。配合后端 `backend/` 运行。

## 准备
- 安装并打开微信开发者工具，使用您的 AppID。
- 在“项目设置 → 开发设置 → 不校验合法域名”勾选（仅开发），或在“业务域名”添加后端地址。

## 目录结构
- `app.json / app.js / app.wxss`: 小程序基础配置
- `project.config.json`: 项目配置（请替换 `appid`）
- `config.js`: 配置后端 `baseUrl` 与可选 `token`
- `utils/request.js`: 封装请求，自动带 `X-User-ID` 与可选 `Authorization`
- `pages/index/*`: 单屏页面（输入、发送、模式切换、档案弹窗、历史加载）

## 运行
1. 后端启动（示例）：
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 --reload False
   ```
2. 微信开发者工具中导入本目录作为小程序项目。
3. 修改 `config.js` 中的 `baseUrl` 指向后端。
4. 点击预览或真机调试。

## 交互说明
- 首次发送消息若无会话ID，后端会创建并返回；前端将其缓存到 `wx.setStorageSync('X_SESSION_ID')`。
- 请求头自动加：`X-User-ID`（开发模式随机生成并缓存）。
- 档案弹窗支持提交到 `/profile`（若已存在将自动 `PUT` 更新）。
- 历史加载调用 `/history`，自动合并并缓存。
- 语音按钮为示例入口，可后续接入同声传译/云函数。

## 注意
- 当前后端基于头部 `X-User-ID` 与可选 `X-Session-ID`，文档中的 `token` 为可选增强；后端忽略未知头。
- UI 维持极简风格，优先保证可跑与链路打通。
