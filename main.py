from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import hashlib
import hmac
import datetime
import requests
import json
import os

# 使用标准 print 输出日志，最稳妥
def log(msg):
    print(f"[Cheaf-Log] {msg}", flush=True)

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware
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
    # 移除微秒
    now = datetime.datetime.utcnow().replace(microsecond=0)
    iso_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_short = now.strftime("%Y%m%d")
    
    headers["x-date"] = iso_date
    headers["host"] = "visual.volcengineapi.com"
    
    canonical_uri = path
    canonical_query = "&".join([f"{k}={v}" for k, v in sorted(query.items())])
    sorted_headers = sorted(headers.items())
    canonical_headers = "".join([f"{k.lower()}:{v.strip()}\n" for k, v in sorted_headers])
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
    
    auth = f"HMAC-SHA256 Credential={ak}/{credential_scope}, SignedHeaders={signedHeaders}, Signature={signature}"
    headers["Authorization"] = auth
    return headers

@app.get("/")
def read_root():
    log("Health check ping received")
    return {"status": "Cheaf Backend is running"}

@app.post("/api/generate_video")
def generate_video(req: VideoRequest):
    log(f"Received generation request for prompt: {req.prompt[:20]}...")
    
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
        signed_headers = sign_request("POST", path, query, headers, body_str, req.access_key, req.secret_key)
        url = f"https://{host}{path}?Action=CVProcess&Version=2022-08-31"
        
        log(f"Sending to Volcengine: {url}")
        resp = requests.post(url, headers=signed_headers, data=body_str)
        
        log(f"Volcengine HTTP Status: {resp.status_code}")
        
        # 即使报错，也尝试返回原文，而不是直接抛出 500
        try:
            return resp.json()
        except:
            log(f"Non-JSON response: {resp.text}")
            return {"code": -1, "message": "Volcengine Error (Non-JSON)", "raw": resp.text}
            
    except Exception as e:
        log(f"Internal Exception: {str(e)}")
        # 捕获所有错误，返回 400 给前端，而不是 500
        raise HTTPException(status_code=400, detail=f"Backend Exception: {str(e)}")

@app.post("/api/check_status")
def check_status(req: StatusRequest):
    host = "visual.volcengineapi.com"
    path = "/"
    query = {"Action": "CVProcess", "Version": "2022-08-31"}
    body_obj = {"req_key": "video_generation", "task_id": req.task_id}
    body_str = json.dumps(body_obj)
    headers = {"content-type": "application/json"}
    
    try:
        signed_headers = sign_request("POST", path, query, headers, body_str, req.access_key, req.secret_key)
        url = f"https://{host}{path}?Action=CVProcess&Version=2022-08-31"
        resp = requests.post(url, headers=signed_headers, data=body_str)
        try:
            return resp.json()
        except:
            return {"code": -1, "message": "Non-JSON response", "raw": resp.text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)