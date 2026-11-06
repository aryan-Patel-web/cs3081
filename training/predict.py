import json, sys, torch
from transformers import AutoModelForCausalLM, AutoTokenizer
model_path = sys.argv[1]; infile = sys.argv[2]; outfile = sys.argv[3]
tok = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float32)
model.eval()
with open(infile) as f, open(outfile, "w") as out:
    for line in f:
        r = json.loads(line)
        prompt = f"Command: {r['text']} JSON:"
        ids = tok(prompt, return_tensors="pt")["input_ids"]
        with torch.no_grad():
            gen = model.generate(ids, max_new_tokens=80, do_sample=False, pad_token_id=tok.eos_token_id)
        txt = tok.decode(gen[0][ids.shape[1]:], skip_special_tokens=True).strip()
        out.write(json.dumps({"id": r["id"], "prediction": txt}) + "\n")
print("wrote", outfile)
