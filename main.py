from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time
import hashlib
import hmac
import datetime
import requests
import json

app = FastAPI()

# 允许跨域请求 (CORS)，这样您的 React 前端才能访问这里
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议限制域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义前端传过来的数据格式
class VideoRequest(BaseModel):
    prompt: str
    access_key: str
    secret_key: str
    ratio: str = "16:9"

class StatusRequest(BaseModel):
    task_id: str
    access_key: str
    secret_key: str

# --- 火山引擎签名算法 (最复杂的部分，我们帮您封装好了) ---
def sign_request(method, path, query, headers, body, ak, sk):
    # 1. 准备时间
    now = datetime.datetime.utcnow()
    iso_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_short = now.strftime("%Y%m%d")
    
    headers["x-date"] = iso_date
    headers["host"] = "visual.volcengineapi.com"
    
    # 2. 规范化请求
    canonical_uri = path
    canonical_query = "&".join([f"{k}={v}" for k, v in sorted(query.items())])
    sorted_headers = sorted(headers.items())
    canonical_headers = "".join([f"{k.lower()}:{v.strip()}\n" for k, v in sorted_headers])
    signed_headers = ";".join([k.lower() for k, v in sorted_headers])
    payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    
    canonical_request = f"{method}\n{canonical_uri}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    
    # 3. 计算签名 Key
    credential_scope = f"{date_short}/cn-north-1/cv/request"
    string_to_sign = f"HMAC-SHA256\n{iso_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    
    def get_hmac(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    k_date = get_hmac(sk.encode('utf-8'), date_short)
    k_region = get_hmac(k_date, "cn-north-1")
    k_service = get_hmac(k_region, "cv")
    k_signing = get_hmac(k_service, "request")
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # 4. 构造 Authorization 头
    auth = f"HMAC-SHA256 Credential={ak}/{credential_scope}, SignedHeaders={signedHeaders}, Signature={signature}"
    headers["Authorization"] = auth
    return headers

# --- API 接口 ---

@app.get("/")
def read_root():
    return {"status": "Cheaf Backend is running"}

@app.post("/api/generate_video")
def generate_video(req: VideoRequest):
    host = "visual.volcengineapi.com"
    path = "/"
    query = {
        "Action": "CVProcess",
        "Version": "2022-08-31"
    }
    
    # 构造请求体
    body_obj = {
        "req_key": "video_generation",
        "prompt": req.prompt,
        "ratio": req.ratio,
        "model_version": "general_v3"
    }
    body_str = json.dumps(body_obj)
    
    headers = {
        "content-type": "application/json"
    }
    
    try:
        # 执行签名
        signed_headers = sign_request("POST", path, query, headers, body_str, req.access_key, req.secret_key)
        url = f"https://{host}{path}?Action=CVProcess&Version=2022-08-31"
        
        # 发送真实请求给火山引擎
        resp = requests.post(url, headers=signed_headers, data=body_str)
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/check_status")
def check_status(req: StatusRequest):
    host = "visual.volcengineapi.com"
    path = "/"
    query = {
        "Action": "CVProcess",
        "Version": "2022-08-31"
    }
    
    body_obj = {
        "req_key": "video_generation",
        "task_id": req.task_id
    }
    body_str = json.dumps(body_obj)
    
    headers = {
        "content-type": "application/json"
    }
    
    try:
        signed_headers = sign_request("POST", path, query, headers, body_str, req.access_key, req.secret_key)
        url = f"https://{host}{path}?Action=CVProcess&Version=2022-08-31"
        
        resp = requests.post(url, headers=signed_headers, data=body_str)
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))