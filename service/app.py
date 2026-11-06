import os, json, re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import torch
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
from transformers import AutoModelForCausalLM, AutoTokenizer
MODEL_URI = os.environ.get("MODEL_URI", "models/v1")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "v1")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "80"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0")
app = FastAPI()
model = None
tok = None
loaded = False
with open("service/schema.json") as f:
    SCHEMA = json.load(f)
KEYS = set(SCHEMA["keys"])
INTENTS = set(SCHEMA["intents"])
def load_model():
    global model, tok, loaded
    path = MODEL_URI
    if path.startswith("s3://"):
        import boto3
        from urllib.parse import urlparse
        u = urlparse(path)
        bucket = u.netloc
        prefix = u.path.lstrip("/")
        s3 = boto3.client("s3", endpoint_url=S3_ENDPOINT, aws_access_key_id=os.environ.get("S3_ACCESS_KEY", "minio"), aws_secret_access_key=os.environ.get("S3_SECRET_KEY", "minio123"))
        os.makedirs("/tmp/model", exist_ok=True)
        for obj in s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("Contents", []):
            key = obj["Key"]
            local = "/tmp/model/" + key.split("/")[-1]
            s3.download_file(bucket, key, local)
        path = "/tmp/model"
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
    model.eval()
    loaded = True
@app.on_event("startup")
def startup():
    load_model()
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
@app.get("/readyz")
def readyz():
    if not loaded:
        return JSONResponse({"status": "not ready"}, status_code=503)
    return {"status": "ready"}
@app.post("/parse")
async def parse(req: Request):
    body = await req.json()
    text = body.get("text", "")
    if FAULT_INJECT == "1":
        raw = "not json"
    else:
        prompt = f"Command: {text} JSON:"
        ids = tok(prompt, return_tensors="pt")["input_ids"]
        with torch.no_grad():
            gen = model.generate(ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False, pad_token_id=tok.eos_token_id)
        raw = tok.decode(gen[0][ids.shape[1]:], skip_special_tokens=True).strip()
    try:
        obj, _ = json.JSONDecoder().raw_decode(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return JSONResponse({"error": "invalid_model_output"}, status_code=500)
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return JSONResponse({"error": "invalid_model_output"}, status_code=500)
    if not isinstance(obj, dict) or set(obj.keys()) != KEYS or obj.get("intent") not in INTENTS:
        return JSONResponse({"error": "invalid_model_output"}, status_code=500)
    headers = {"X-Model-Version": MODEL_VERSION, "X-Served-By": os.environ.get("HOSTNAME", "local")}
    return JSONResponse(content=obj, headers=headers)
