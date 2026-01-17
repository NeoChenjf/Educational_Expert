/**
 * 前端配置读取
 * 
 * 说明：
 * - baseUrl：后端服务根地址；开发阶段可以指向本机（需关闭合法域名校验或配置测试域名）。
 * - token：可选的 Bearer Token；当前后端主要依赖请求头 `X-User-ID` 与可选 `X-Session-ID`。
 */
export function getConfig() {
  return {
    // 本地开发后端地址（需在微信开发者工具里配置合法域名或关闭校验用于本地联调）
    baseUrl: 'http://127.0.0.1:8000',
    // 可选：后端若需要 Bearer Token，可设置；当前后端主要使用 X-User-ID
    token: ''
  }
}
