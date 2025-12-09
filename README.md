# Cheaf Backend (Python FastAPI)

这是 Cheaf 1.0 的后端服务，用于解决浏览器直接调用 AI 接口时的跨域 (CORS) 问题。

## 部署步骤 (使用 Zeabur - 推荐小白)

1. **准备代码**
   - 确保 `backend` 文件夹里有 `main.py` 和 `requirements.txt`。
   - 如果您是从 Cheaf 源代码中下载的，请将整个 `backend` 文件夹作为一个新的 Git 仓库，或者保留在根目录下。

2. **推送到 GitHub**
   - 将代码提交到您的 GitHub 仓库。

3. **在 Zeabur 部署**
   - 登录 [Zeabur Dashboard](https://dash.zeabur.com)。
   - 点击 **Create Project** (创建项目)。
   - 点击 **New Service** (新建服务) -> **GitHub**。
   - 选择您刚才上传的仓库。
   - Zeabur 会自动检测到 Python 项目并开始构建。

4. **获取域名**
   - 部署成功后，在 Zeabur 的 **Networking** (网络) 选项卡中，生成一个域名。
   - 例如：`https://cheaf-api-xxxxx.zeabur.app`。

5. **配置前端**
   - 回到 Cheaf 前端网页。
   - 打开左下角的 **API 设置**。
   - 在 **后端代理地址** 中填入上面的域名。
   - 填入您的 AccessKey 和 SecretKey。
   - 此时，前端将通过这个后端地址真实调用火山引擎 API。

## 本地运行 (可选)

如果您安装了 Python：

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

后端将在 `http://127.0.0.1:8000` 运行。
