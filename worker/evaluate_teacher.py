import json, subprocess, urllib.request
prompt = open("prompts/teacher_prompt.txt").read()
host = subprocess.check_output("ip route | awk '/default/ {print $3}'", shell=True, text=True).strip()
url = f"http://{host}:11434/api/generate"
dec = json.JSONDecoder()
out = open("results/pred_teacher.jsonl", "w")
rows = [json.loads(l) for l in open("data/validation.jsonl")]
for i, r in enumerate(rows):
    full = prompt + f"\nCommand: {r['text']}\nJSON:"
    data = json.dumps({"model": "phi3.5", "prompt": full, "stream": False, "options": {"temperature": 0, "seed": 42, "num_predict": 100, "stop": ["\n\nCommand:", "\nCommand:"]}}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = json.loads(resp.read().decode()).get("response", "")
    pred = raw.strip()
    try:
        start = raw.find("{")
        obj, _ = dec.raw_decode(raw[start:])
        pred = json.dumps(obj)
    except Exception:
        pred = raw.strip()
    out.write(json.dumps({"id": r["id"], "prediction": pred}) + "\n")
    out.flush()
    if i % 20 == 0:
        print(i, r["id"])
print("wrote results/pred_teacher.jsonl")
