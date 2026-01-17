/**
 * 小程序应用入口
 * 
 * 说明：
 * - 读取前端配置（后端 baseUrl 与可选 token）并保存到全局。
 * - 生成或复用一个开发阶段的用户标识 `X-User-ID`，用于后端侧识别用户与管理会话。
 * - 真实生产环境应使用微信登录换取 openid/unionid 作为用户唯一标识。
 */
import { getConfig } from './config.js'

App({
  /**
   * 全局数据：
   * - baseUrl: 后端接口根地址
   * - token: 可选的鉴权 Token，将作为 `Authorization: Bearer <token>` 传递
   * - userId: 当前用户标识（开发阶段生成，生产应替换为 openid/unionid）
   */
  globalData: {
    baseUrl: '',
    token: '',
    userId: '',
  },

  /**
   * 小程序启动时执行：
   * - 加载配置
   * - 初始化或复用用户标识
   */
  onLaunch() {
    const cfg = getConfig()
    this.globalData.baseUrl = cfg.baseUrl
    this.globalData.token = cfg.token

    // 简易生成或复用用户ID（真实环境可用登录/openid）
    const cached = wx.getStorageSync('X_USER_ID')
    if (cached) {
      this.globalData.userId = cached
    } else {
      // 使用时间戳构造一个可读的开发期 ID
      const uid = `dev_${Date.now()}`
      this.globalData.userId = uid
      wx.setStorageSync('X_USER_ID', uid)
    }
  }
})
