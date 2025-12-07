# Cheaf 后端服务

这是一个基于 Python FastAPI 的轻量级后端，用于 Cheaf 1.0 视频生成平台。

## 主要功能
它充当了 React 前端和火山引擎（即梦）API 之间的安全代理，主要解决：
1. 浏览器跨域 (CORS) 限制。
2. 在服务器端进行复杂的 HMAC-SHA256 签名。

## 部署
本项目设计为可以直接部署在 Zeabur 或 Vercel 等 Serverless 平台。