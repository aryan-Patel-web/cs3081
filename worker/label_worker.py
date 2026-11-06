import os, json, urllib.request, subprocess
SHARD_INDEX = int(os.environ.get("SHARD_INDEX", "0"))
SHARD_COUNT = int(os.environ.get("SHARD_COUNT", "1"))
host = subprocess.check_output("ip route | awk '/default/ {print $3}'", shell=True, text=True).strip()
OLLAMA_URL = os.environ.get("OLLAMA_URL", f"http://{host}:11434/api/generate")
with open("prompts/teacher_prompt.txt") as f:
    PROMPT = f.read().strip()
os.makedirs("teacher", exist_ok=True)
out_path = f"teacher/shard-{SHARD_INDEX}.jsonl"
done = set()
if os.path.exists(out_path):
    with open(out_path) as f:
        for line in f:
            try: done.add(json.loads(line)["id"])
            except: pass
with open("data/commands_pool.jsonl") as f:
    lines = f.readlines()
with open(out_path, "a") as out:
    for i, line in enumerate(lines):
        if i % SHARD_COUNT != SHARD_INDEX:
            continue
        rec = json.loads(line)
        if rec["id"] in done:
            continue
        body = json.dumps({"model": "phi3.5", "prompt": PROMPT + "\nCommand: " + rec["text"] + "\nJSON:", "stream": False, "options": {"temperature": 0, "seed": 42, "num_predict": 100, "stop": ["\n\nCommand:", "\nCommand:"]}}).encode()
        req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = json.loads(r.read())["response"]
        except Exception as e:
            print(f"{rec['id']} ERROR {e}", flush=True)
            continue
        out.write(json.dumps({"id": rec["id"], "text": rec["text"], "teacher_raw": raw}) + "\n")
        out.flush()
        if i % 20 == 0:
            print(f"shard {SHARD_INDEX} done line {i} id {rec['id']}", flush=True)
print(f"shard {SHARD_INDEX} finished", flush=True)
