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

# 日志工具
def log(msg):
    print(f"[Cheaf] {msg}", file=sys.stdout, flush=True)

app = FastAPI()

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

def sign_request(method, path, query, headers, body_bytes, ak, sk):
    # 1. 准备时间
    now = datetime.datetime.utcnow().replace(microsecond=0)
    iso_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_short = now.strftime("%Y%m%d")
    
    # 2. 补充必要 Header
    headers["x-date"] = iso_date
    headers["host"] = "visual.volcengineapi.com"
    
    # 3. 规范化
    canonical_uri = path
    canonical_query = "&".join([f"{k}={v}" for k, v in sorted(query.items())])
    
    sorted_headers = sorted(headers.items())
    canonical_headers = "".join([f"{k.lower()}:{v.strip()}\n" for k, v in sorted_headers])
    signed_headers = ";".join([k.lower() for k, v in sorted_headers])
    
    # 4. 计算 Body 哈希 (对原始二进制进行哈希)
    payload_hash = hashlib.sha256(body_bytes).hexdigest()
    
    canonical_request = f"{method}\n{canonical_uri}\n{canonical_query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    
    # 5. 签名计算
    credential_scope = f"{date_short}/cn-north-1/cv/request"
    string_to_sign = f"HMAC-SHA256\n{iso_date}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    
    def get_hmac(key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    k_date = get_hmac(sk.encode('utf-8'), date_short)
    k_region = get_hmac(k_date, "cn-north-1")
    k_service = get_hmac(k_region, "cv")
    k_signing = get_hmac(k_service, "request")
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    auth = f"HMAC-SHA256 Credential={ak}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
    headers["Authorization"] = auth
    return headers

@app.get("/")
def read_root():
    log("Health Check OK")
    return {"status": "Cheaf Backend is running"}

@app.post("/api/generate_video")
def generate_video(req: VideoRequest):
    log(f"New Task: {req.prompt[:20]}...")
    
    host = "visual.volcengineapi.com"
    path = "/"
    query = {"Action": "CVProcess", "Version": "2022-08-31"}
    
    body_obj = {
        "req_key": "video_generation",
        "prompt": req.prompt,
        "ratio": req.ratio,
        "model_version": "general_v3"
    }
    
    # 关键修改：使用默认的 json.dumps
    # 这样中文会被转义为 \uXXXX (纯 ASCII)，这是最安全的签名方式，避免编码不一致
    body_str = json.dumps(body_obj)
    body_bytes = body_str.encode('utf-8')
    
    headers = {"content-type": "application/json"}
    
    try:
        log("Signing request...")
        signed_headers = sign_request("POST", path, query, headers, body_bytes, req.access_key, req.secret_key)
        
        url = f"https://{host}{path}?Action=CVProcess&Version=2022-08-31"
        log("Sending to Volcengine...")
        
        # 必须使用 data=body_bytes，确保发送的内容和签名的内容比特级一致
        resp = requests.post(url, headers=signed_headers, data=body_bytes)
        
        log(f"Volcengine Status: {resp.status_code}")
        if resp.status_code != 200:
            log(f"Error Body: {resp.text}")
            
        try:
            return resp.json()
        except:
            return {"code": -1, "message": "Non-JSON response", "raw": resp.text}
            
    except Exception as e:
        log(f"Crash: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/check_status")
def check_status(req: StatusRequest):
    host = "visual.volcengineapi.com"
    path = "/"
    query = {"Action": "CVProcess", "Version": "2022-08-31"}
    body_obj = {"req_key": "video_generation", "task_id": req.task_id}
    
    # 同样的 ASCII 安全处理
    body_str = json.dumps(body_obj)
    body_bytes = body_str.encode('utf-8')
    headers = {"content-type": "application/json"}
    
    try:
        signed_headers = sign_request("POST", path, query, headers, body_bytes, req.access_key, req.secret_key)
        url = f"https://{host}{path}?Action=CVProcess&Version=2022-08-31"
        resp = requests.post(url, headers=signed_headers, data=body_bytes)
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)