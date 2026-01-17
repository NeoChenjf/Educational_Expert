import { apiRequest } from '../../utils/request.js'

/**
 * 单页聊天与档案管理逻辑
 * 
 * 功能概览：
 * - 模式切换（concise/detailed）影响后端回复风格。
 * - 消息列表：展示用户与 AI 的对话。
 * - 输入与发送：调用后端聚合接口 `/chat_with_context`，自动带档案年龄与历史。
 * - 会话管理：复用后端返回的 `session_id`，保存在本地并继续透传于请求头。
 * - 档案表单：GET/POST/PUT `/profile`，支持轻量弹窗编辑与保存。
 * - 历史加载：GET `/history`，合并并缓存。
 * - 语音按钮：保留占位，后续可接入同声传译或云函数。
 */
Page({
  data: {
    // 回复模式：简洁/详细
    mode: 'concise',
    // 消息数组：{ role: 'user'|'assistant', content: string }
    messages: [],
    // 文本输入框内容
    inputText: '',
    // 加载态：发送过程中禁用按钮与展示提示
    loading: false,
    // 简易安全提示文本：响应包含不当建议时显示
    warnText: '',
    // 是否显示档案弹窗
    showProfile: false,
    // 档案数据模型（与后端 schemas 对齐）
    profile: {
      nickname: '',
      birth_date: '',
      grade: '',
      notes: ''
    },
    // 会话ID：后端创建后返回，前端本地持久化并复用
    sessionId: ''
  },

  /**
   * 页面加载：
   * - 从本地缓存恢复会话ID与消息列表，提升用户体验。
   */
  onLoad() {
    // 读取缓存的会话ID与本地消息
    const sid = wx.getStorageSync('X_SESSION_ID')
    if (sid) {
      this.setData({ sessionId: sid })
    }
    const cachedMsgs = wx.getStorageSync('LOCAL_MESSAGES') || []
    if (cachedMsgs.length) {
      this.setData({ messages: cachedMsgs })
    }
  },

  // 文本输入绑定
  onInput(e) { this.setData({ inputText: e.detail.value }) },

  // 模式切换（radio）
  onModeChange(e) { this.setData({ mode: e.detail.value }) },

  /**
   * 发送消息：
   * - 写入本地“用户消息”以提升响应速度与交互感。
   * - 调用 `/chat_with_context` 后获取 AI 回复并写入历史。
   * - 首次无 sessionId 时，后端会创建并返回，前端持久化保存。
   */
  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text) return
    if (this.data.loading) return

    this.setData({ loading: true, warnText: '' })

    // 先写入本地消息（用户），并清空输入框
    const newMsgs = this.data.messages.concat([{ role: 'user', content: text }])
    this.setData({ messages: newMsgs, inputText: '' })

    try {
      const headers = {}
      // 复用会话ID（如存在），后端将关联到对应历史
      if (this.data.sessionId) headers['X-Session-ID'] = this.data.sessionId

      const resp = await apiRequest({
        path: '/chat_with_context',
        method: 'POST',
        headers,
        data: {
          message: text,
          response_mode: this.data.mode,
          history_limit: 10 // 上下文取最近 N 条，避免过长导致响应变慢
        }
      })

      // 持久化会话ID（仅首次创建或切换时）
      if (resp.session_id && resp.session_id !== this.data.sessionId) {
        this.setData({ sessionId: resp.session_id })
        wx.setStorageSync('X_SESSION_ID', resp.session_id)
      }

      // 写入AI回复并持久化本地消息
      const msgs2 = this.data.messages.concat([{ role: 'assistant', content: resp.reply || '' }])
      this.setData({ messages: msgs2 })
      wx.setStorageSync('LOCAL_MESSAGES', msgs2)

      // 简易“安全提示”示例（服务端若返回特定标记可增强）
      if ((resp.reply || '').includes('不当建议')) {
        this.setData({ warnText: '⚠️ 检测到不当建议，请换种问法。' })
      }
    } catch (err) {
      // 网络或后端错误提示
      wx.showToast({ title: '请求失败', icon: 'none' })
      console.error('chat_with_context error', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 加载历史（云端）：
   * - 若本地已有会话ID则透传到请求头，后端返回该会话的完整历史。
   * - 返回后只保留 role+content 并覆盖本地缓存。
   */
  async loadHistory() {
    try {
      const headers = {}
      if (this.data.sessionId) headers['X-Session-ID'] = this.data.sessionId

      const data = await apiRequest({ path: '/history', method: 'GET', headers })
      if (data && data.messages) {
        const msgs = data.messages.map(m => ({ role: m.role, content: m.content }))
        this.setData({ messages: msgs })
        wx.setStorageSync('LOCAL_MESSAGES', msgs)
        if (data.session_id && !this.data.sessionId) {
          this.setData({ sessionId: data.session_id })
          wx.setStorageSync('X_SESSION_ID', data.session_id)
        }
      }
    } catch (err) {
      wx.showToast({ title: '历史加载失败', icon: 'none' })
      console.error('history error', err)
    }
  },

  /**
   * 打开档案弹窗，并尝试从后端拉取档案数据：
   * - 若后端不存在档案，保持空表单（仍可对话）。
   */
  openProfile() {
    // 读取后端档案或本地缓存
    this.setData({ showProfile: true })
    this.fetchProfile()
  },

  // 关闭档案弹窗
  closeProfile() { this.setData({ showProfile: false }) },

  // 档案输入绑定：根据 data-key 更新本地 profile
  onProfileInput(e) {
    const key = e.currentTarget.dataset.key
    const value = e.detail.value
    const pf = { ...this.data.profile, [key]: value }
    this.setData({ profile: pf })
  },

  /**
   * 从后端查询档案：
   * - 成功后填充表单；失败（无档案）则忽略。
   */
  async fetchProfile() {
    try {
      const prof = await apiRequest({ path: '/profile', method: 'GET' })
      if (prof && prof.nickname) this.setData({ profile: {
        nickname: prof.nickname,
        birth_date: (prof.birth_date || '').split('T')[0] || '',
        grade: prof.grade || '',
        notes: prof.notes || ''
      } })
    } catch (err) {
      // 无档案也可对话
      console.info('no profile or fetch error', err)
    }
  },

  /**
   * 提交档案：
   * - 优先尝试 POST 创建；若已存在则回退到 PUT 更新。
   * - 成功后关闭弹窗并提示。
   */
  async submitProfile() {
    const { nickname, birth_date } = this.data.profile
    if (!nickname || !birth_date) {
      wx.showToast({ title: '请填写昵称和出生日期', icon: 'none' })
      return
    }
    try {
      await apiRequest({ path: '/profile', method: 'POST', data: this.data.profile })
      wx.showToast({ title: '档案已保存', icon: 'success' })
      this.setData({ showProfile: false })
    } catch (err) {
      // 若已存在，尝试更新
      try {
        await apiRequest({ path: '/profile', method: 'PUT', data: this.data.profile })
        wx.showToast({ title: '档案已更新', icon: 'success' })
        this.setData({ showProfile: false })
      } catch (err2) {
        wx.showToast({ title: '档案保存失败', icon: 'none' })
        console.error('profile save error', err2)
      }
    }
  },

  /**
   * 语音输入占位：
   * - 后续可接入微信同声传译或云函数上传音频、调用语音识别并回填文本再发送。
   */
  recordVoice() {
    wx.showToast({ title: '语音暂为示例', icon: 'none' })
    // 可接入同声传译或录音+云函数转文字再发送
  }
})
