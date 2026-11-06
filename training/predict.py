import sys, json, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
model_path, infile, outfile = sys.argv[1], sys.argv[2], sys.argv[3]
tok = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float32)
model.eval()
dec = json.JSONDecoder()
out = open(outfile, "w")
for line in open(infile):
    r = json.loads(line)
    prompt = f"Command: {r['text']} JSON:"
    ids = tok(prompt, return_tensors="pt")
    with torch.no_grad():
        gen = model.generate(**ids, max_new_tokens=80, do_sample=False, pad_token_id=tok.eos_token_id)
    raw = tok.decode(gen[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)
    pred = raw.strip()
    try:
        start = raw.find("{")
        obj, _ = dec.raw_decode(raw[start:])
        pred = json.dumps(obj)
    except Exception:
        pred = raw.strip()
    out.write(json.dumps({"id": r["id"], "prediction": pred}) + "\n")
    out.flush()
out.close()
print("wrote", outfile)
