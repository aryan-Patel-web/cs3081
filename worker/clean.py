import json, hashlib, os, glob
INTENTS = {"alarm_set","alarm_query","calendar_set","calendar_query","calendar_remove","weather_query","datetime_query","recommendation_events"}
records = []
for path in sorted(glob.glob("teacher/shard-*.jsonl")):
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
counts = {"input": len(records), "a_invalid_json": 0, "b_bad_keys": 0, "c_bad_intent": 0, "d_bad_slot": 0, "duplicates": 0, "kept": 0}
kept = []
seen_text = {}
for r in sorted(records, key=lambda x: x["id"]):
    raw = r.get("teacher_raw", "")
    try:
        obj = json.loads(raw.strip())
    except:
        counts["a_invalid_json"] += 1
        continue
    if not isinstance(obj, dict) or set(obj.keys()) != {"intent","date","time","place"}:
        counts["b_bad_keys"] += 1
        continue
    if obj["intent"] not in INTENTS:
        counts["c_bad_intent"] += 1
        continue
    text_low = r["text"].lower()
    bad = False
    for k in ("date","time","place"):
        v = obj[k]
        if v is not None and (not isinstance(v, str) or v.lower() not in text_low):
            bad = True
    if bad:
        counts["d_bad_slot"] += 1
        continue
    if r["text"] in seen_text:
        counts["duplicates"] += 1
        continue
    seen_text[r["text"]] = r["id"]
    kept.append({"id": r["id"], "text": r["text"], "intent": obj["intent"], "date": obj["date"], "time": obj["time"], "place": obj["place"]})
counts["kept"] = len(kept)
os.makedirs("datasets/v1", exist_ok=True)
os.makedirs("results", exist_ok=True)
with open("datasets/v1/train.jsonl", "w") as f:
    for k in kept:
        f.write(json.dumps(k) + "\n")
data = open("datasets/v1/train.jsonl","rb").read()
open("datasets/v1/train.sha256","w").write(hashlib.sha256(data).hexdigest() + "  train.jsonl\n")
open("results/clean_counts.json","w").write(json.dumps(counts, indent=2))
print(counts)
print("input = a+b+c+d+duplicates+kept ?", counts["input"] == counts["a_invalid_json"]+counts["b_bad_keys"]+counts["c_bad_intent"]+counts["d_bad_slot"]+counts["duplicates"]+counts["kept"])
