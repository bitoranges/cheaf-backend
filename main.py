import os
import sys
import json
import hmac
import hashlib
import datetime
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. 强制日志输出到控制台 (解决 Zeabur 看不到日志的问题)
def log(msg):
    print(f"[Cheaf] {msg}", file=sys.stdout, flush=True)

app = FastAPI()

# 2. 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    prompt: str
    access_key: str
    secret_key: str
    ratio: str = "16:9"

class StatusRequest(BaseModel):
    task_id: str
    access_key: str
    secret_key: str

def sign_request(method, path, query, headers, body, ak, sk):
    # 移除微秒，防止时间格式不匹配
    now = datetime.datetime.utcnow().replace(microsecond=0)
    iso_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_short = now.strftime("%Y%m%d")
    
    headers["x-date"] = iso_date
    headers["host"] = "visual.volcengineapi.com"
    
    canonical_uri = path
    canonical_query = "&".join([f"{k}={v}" for k, v in sorted(query.items())])
    sorted_headers = sorted(headers.items())
    canonical_headers = "".join([f"{k.lower()}:{v.strip()}\n" for k, v in sorted_headers])
    
    # 变量定义为 signed_headers (下划线)
    signed_headers = ";".join([k.lower() for k, v in sorted_headers])
    
    payload_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    
    canonical_request = f"{method}\n{canonical_uri}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    
    credential_scope = f"{date_short}/cn-north-1/cv/request"
    string_to_sign = f"HMAC-SHA256\n{iso_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    
    def get_hmac(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    k_date = get_hmac(sk.encode('utf-8'), date_short)
    k_region = get_hmac(k_date, "cn-north-1")
    k_service = get_hmac(k_region, "cv")
    k_signing = get_hmac(k_service, "request")
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # 修复 BUG：这里之前写成了 signedHeaders，现在改为 signed_headers (与上面定义一致)
    auth = f"HMAC-SHA256 Credential={ak}/{credential_scope}, signed_headers={signed_headers}, Signature={signature}"
    headers["Authorization"] = auth
    return headers

@app.get("/")
def read_root():
    log("Health Check OK")
    return {"status": "Cheaf Backend is running"}

@app.post("/api/generate_video")
def generate_video(req: VideoRequest):
    log(f"New Task Prompt: {req.prompt[:30]}...")
    
    host = "visual.volcengineapi.com"
    path = "/"
    query = {"Action": "CVProcess", "Version": "2022-08-31"}
    
    body_obj = {
        "req_key": "video_generation",
        "prompt": req.prompt,
        "ratio": req.ratio,
        "model_version": "general_v3"
    }
    body_str = json.dumps(body_obj)
    headers = {"content-type": "application/json"}
    
    try:
        log("Signing request...")
        signed_headers_dict = sign_request("POST", path, query, headers, body_str, req.access_key, req.secret_key)
        url = f"https://{host}{path}?Action=CVProcess&Version=2022-08-31"
        
        log("Sending to Volcengine...")
        resp = requests.post(url, headers=signed_headers_dict, data=body_str)
        
        log(f"Volcengine Response: {resp.status_code}")
        
        # 无论成功失败，尝试解析 JSON 返回给前端，让前端展示具体错误
        try:
            return resp.json()
        except:
            log(f"Non-JSON Response: {resp.text}")
            return {"code": -1, "message": "API Error (Non-JSON)", "raw": resp.text}
            
    except Exception as e:
        log(f"Crash Exception: {str(e)}")
        # 捕获所有 Python 异常，返回 400，防止 500 Internal Server Error
        raise HTTPException(status_code=400, detail=f"Backend Logic Error: {str(e)}")

@app.post("/api/check_status")
def check_status(req: StatusRequest):
    host = "visual.volcengineapi.com"
    path = "/"
    query = {"Action": "CVProcess", "Version": "2022-08-31"}
    body_obj = {"req_key": "video_generation", "task_id": req.task_id}
    body_str = json.dumps(body_obj)
    headers = {"content-type": "application/json"}
    
    try:
        signed_headers_dict = sign_request("POST", path, query, headers, body_str, req.access_key, req.secret_key)
        url = f"https://{host}{path}?Action