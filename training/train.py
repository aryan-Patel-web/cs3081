import os, sys, json, yaml, csv, random
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from torch.utils.data import Dataset
with open("training/config.yaml") as f:
    cfg = yaml.safe_load(f)
subset = int(os.environ.get("SUBSET", "0")) or None
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    subset = int(sys.argv[1])
random.seed(cfg["seed"]); torch.manual_seed(cfg["seed"])
rows = [json.loads(l) for l in open("datasets/v1/train.jsonl")]
if subset:
    rows = rows[:subset]
texts = []
for r in rows:
    obj = {"intent": r["intent"], "date": r["date"], "time": r["time"], "place": r["place"]}
    texts.append(f"Command: {r['text']} JSON: {json.dumps(obj)}")
tok = AutoTokenizer.from_pretrained(cfg["model"])
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
class DS(Dataset):
    def __len__(self): return len(texts)
    def __getitem__(self, i):
        ids = tok(texts[i], truncation=True, max_length=cfg["max_seq_length"])["input_ids"]
        return {"input_ids": ids, "labels": list(ids)}
model = AutoModelForCausalLM.from_pretrained(cfg["model"], torch_dtype=torch.float32)
out = os.environ.get("OUT", "models/v1")
args = TrainingArguments(output_dir="training/out", per_device_train_batch_size=cfg["batch_size"], num_train_epochs=cfg["epochs"], learning_rate=cfg["learning_rate"], logging_steps=5, save_strategy="no", seed=cfg["seed"], report_to=[], remove_unused_columns=False)
trainer = Trainer(model=model, args=args, train_dataset=DS(), data_collator=DataCollatorForLanguageModeling(tok, mlm=False))
trainer.train()
os.makedirs(out, exist_ok=True)
model.save_pretrained(out); tok.save_pretrained(out)
losses = [(h.get("epoch"), h.get("loss")) for h in trainer.state.log_history if "loss" in h]
with open("training/loss.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["epoch", "loss"])
    for e, l in losses: w.writerow([e, l])
print("saved to", out, "loss rows:", losses)
losses = [(h.get("epoch"), h.get("loss")) for h in trainer.state.log_history if "loss" in h]
with open("training/loss.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["epoch", "loss"])
    for e, l in losses: w.writerow([e, l])
print("saved to", out, "loss rows:", losses)
