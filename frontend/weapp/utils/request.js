import { getConfig } from '../config.js'

/**
 * 统一封装 API 请求（wx.request）
 * 
 * 功能：
 * - 自动附加 `X-User-ID`（从全局取用户标识）。
 * - 可叠加自定义请求头（如 `X-Session-ID`）。
 * - 若配置了 token，自动增加 `Authorization: Bearer <token>`。
 * - 成功返回 `res.data`，失败抛出状态码或网络错误。
 */
export function apiRequest({ path, method = 'POST', data = {}, headers = {} }) {
  const cfg = getConfig()
  const app = getApp()

  // 基础请求头：JSON、用户标识
  const baseHeaders = {
    'Content-Type': 'application/json',
    'X-User-ID': app?.globalData?.userId || 'unknown',
    ...headers,
  }

  // 可选 Token
  if (cfg.token) {
    baseHeaders['Authorization'] = `Bearer ${cfg.token}`
  }

  // 使用 Promise 包装 wx.request，统一成功/失败处理
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${cfg.baseUrl}${path}`,
      method,
      data,
      header: baseHeaders,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          // 非 2xx 直接 reject，包含后端返回的错误信息
          reject({ statusCode: res.statusCode, data: res.data })
        }
      },
      fail(err) {
        // 网络错误或请求失败
        reject(err)
      }
    })
  })
}
