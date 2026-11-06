# Cloud Computing Mini Project — Command Parser (CS3081)

Knowledge distillation of a command-parsing model (`phi3.5` teacher → `pythia-70m` student),
served on a local k3d Kubernetes cluster with SeaweedFS object storage.

> **Student:** Aryan Patel · **Roll number:** 230101047 · **Section:** A · B.Tech CSE, IIIT Senapati, Manipur, graduating April 2027 · **Location:** Kanpur · **Repo:** https://github.com/aryan-Patel-web/cs3081

## What it does

Takes one English command and returns a four-key JSON object:

```
POST /parse  {"text": "set an alarm for seven thirty am tomorrow"}
->  {"intent": "alarm_set", "date": "tomorrow", "time": "seven thirty am", "place": null}
```

Intents (8): `alarm_set`, `alarm_query`, `calendar_set`, `calendar_query`, `calendar_remove`, `weather_query`, `datetime_query`, `recommendation_events`.
Slots are copied exactly from the command, shortest phrase, `null` if absent, never invented.

## Prerequisites

| Tool | Used for | Version used here |
|------|----------|-------------------|
| Docker | build images, run k3d | docker.io 29.1.3, inside Ubuntu WSL |
| k3d + kubectl | local Kubernetes | k3d v5.7.4, kubectl v1.31.4 |
| Ollama + `phi3.5` | the teacher | `ollama pull phi3.5` (~2.2 GB), temperature 0, seed 42 |
| Python 3.12 | training, scripts, tests | venv `.venv`, torch 2.15.0+cpu, transformers 5.22.2 |
| make, locust, gh | orchestration, load test, releases | locust 2.47.0 |

> On Windows, work in Ubuntu 24.04 in WSL. In Ubuntu, plain `ollama` is not found, use `ollama.exe`. Paste with right-click / Ctrl+Shift+V, not Ctrl+V. After a WSL restart, restart Docker inside Ubuntu with `sudo service docker start` and `sudo chmod 666 /var/run/docker.sock`.

## Repository layout

```
cluster/      k3d.yaml                     Task 1  cluster config (cs3081, 1 server, 8080:80)
prompts/      teacher_prompt.txt           Task 1  teacher prompt
worker/       label_worker.py, clean.py, evaluate_teacher.py   Task 1/2  sharded labelling + cleaning + teacher eval
training/     train.py, predict.py, config.yaml, config_v2.yaml, loss.csv   Task 2  student training + inference
service/      app.py, Dockerfile, requirements.txt, schema.json   Task 3  FastAPI /parse service
k8s/          00-namespaces.yaml, deployment.yaml, service.yaml, ingress.yaml, hpa.yaml, seaweedfs.yaml   Tasks 1 & 4
network/      subnets.md, nacl.json        Task 5  subnetting + NACL
scripts/      upload_s3.py, make_pdf.py    Tasks 1 & 7  S3 upload + report PDF
tools/        score.py, nacl_sim.py, locustfile.py   provided checkers
tests/        test_subnets.py, test_clean.py, test_nacl.py   Task 6
data/         commands_pool.jsonl, validation.jsonl, schema.json, rate_card.json   provided kit
results/      score reports, clean counts, loss, locust output   Tasks 2 & 7 evidence
report/       report.md, report.pdf        final report (3 pages)
Makefile      up / down / train / clean / test
AI_USE.md     what AI was used for
```

## Quick start

```bash
make up                         # cluster + namespaces + deployment + service + ingress + hpa
make train SUBSET=50            # smoke test (fast)
make train                      # full v1 -> models/v1/
make test                       # pytest, 6 passed
```

## Full workflow

### Task 1 — object storage + parallel teacher labelling

```bash
ollama pull phi3.5
# from Ubuntu, teacher is on Windows host:
curl http://$(ip route | awk '/default/ {print $3}'):11434/api/tags
make up                                      # cluster + namespaces
kubectl apply -f k8s/seaweedfs.yaml          # SeaweedFS in namespace data, S3 on port 8333
kubectl port-forward -n data svc/seaweedfs-filer 8333:8333 &
python3 scripts/upload_s3.py                 # creates buckets datasets + models, uploads commands_pool.jsonl
# labelling, 2 workers in tmux (each skips IDs already written, so a restart resumes):
tmux new -s label0 -d 'SHARD_INDEX=0 SHARD_COUNT=2 .venv/bin/python worker/label_worker.py'
tmux new -s label1 -d 'SHARD_INDEX=1 SHARD_COUNT=2 .venv/bin/python worker/label_worker.py'
wc -l teacher/shard-*.jsonl                  # 1500 + 1500 = 3000 when done
make clean-data                              # -> datasets/v1/train.jsonl + train.sha256, prints counts
```

### Task 2 — train the student

```bash
make train SUBSET=50          # smoke test: 13/13 steps, loss 2.689 -> 1.338
make train                    # full v1, 1500 examples, seed 42 -> models/v1/
# v2, seed 43:
OUT=models/v2 .venv/bin/python training/train.py 0
make test
.venv/bin/python training/predict.py   # writes results/pred_student_v1.jsonl
python3 tools/score.py --help
```

Distillation is sequence-level only. The teacher is reached through Ollama, which returns text only, no logits, so logit-based distillation is impossible here. The student is trained only on teacher replies, never on `validation.jsonl`.

### Task 3 — the container

```bash
docker build -t parser:v1 -f service/Dockerfile .
docker images parser:v1           # 1.82 GB, under 2 GB, no weights inside
# local smoke test, 1 CPU / 1 GiB:
docker run --rm -p 8000:8000 -e MODEL_URI=models/v1 -e MODEL_VERSION=v1 parser:v1
curl -s -X POST http://localhost:8000/parse -H 'Content-Type: application/json' -d '{"text":"set an alarm for seven thirty am tomorrow"}'
# with FAULT_INJECT=1 -> HTTP 500 {"error":"invalid_model_output"}
```

Fix that made the local test work: `torch.set_num_threads(1)` in `service/app.py`. Before that, with many threads on 1 CPU, `/parse` hung for over 120 s at 100% CPU. The Dockerfile needs `--extra-index-url https://download.pytorch.org/whl/cpu` for `torch==2.15.0+cpu`.

### Task 4 — deploy, scale, reliability

```bash
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/ingress.yaml -f k8s/hpa.yaml
kubectl -n app get deploy,svc,ingress,hpa,pods
curl -s -i -X POST http://localhost:8080/parse -H 'Content-Type: application/json' -d '{"text":"set an alarm for seven thirty am tomorrow"}'
# rolling update v1 -> v2:
docker build -t parser:v2 -f service/Dockerfile .
k3d image import parser:v2 -c cs3081
kubectl set image deployment/parser parser=parser:v2 -n app
kubectl set env deployment/parser MODEL_VERSION=v2 MODEL_URI=s3://models/v2 -n app
kubectl rollout status deployment/parser -n app
# rollback:
kubectl rollout undo deployment/parser -n app
```

### Task 5 — networking (self-contained, no cluster)

```bash
python3 tools/nacl_sim.py network/nacl.json network/packets_sample.jsonl --check   # 6/6 = 100.0%
```

Subnets, from `10.20.0.0`, largest to smallest: app `10.20.0.0/22` (1022 usable), public `10.20.4.0/24` (254), data `10.20.5.0/25` (126), management `10.20.5.128/27` (30). Next free: `10.20.5.160`. See `network/subnets.md`.

### Task 6 — tests & CI

```bash
make test        # pytest, 6 passed in 0.02s
```

CI (`.github/workflows/ci.yml`): lint → tests → evaluate (`score.py`) → gate (`score.py --min-validity 95`) → secret-scan (gitleaks). Student v1 passes the gate at 98.0% validity. The untrained base scores 0.0% and would fail the gate, as expected.

### Task 7 — performance & cost

```bash
.venv/bin/locust -f tools/locustfile.py --host http://localhost:8080 --users 4 --spawn-rate 4 --run-time 2m --headless --csv results/loadtest
```

## Results

| Item | Measured result |
|------|-----------------|
| Labelling | 3000/3000, shard-0 1500, shard-1 1500 |
| Cleaning | input 3000, invalid JSON 158, bad keys 126, bad intent 29, bad slot 219, duplicates 41, kept 2427 |
| Training v1 | 1500 examples, 375 steps, 265.6 s, train_loss 1.041, loss 2.61 → 0.64 |
| Training v2 | seed 43, 239.8 s, train_loss 1.04, loss 2.65 → 0.82 |
| Base pythia-70m | validity 0, intent 0, date 0, time 0, place 0, full frame 0 |
| Teacher phi3.5 | validity 93, intent 66, date 66, time 76, place 68, full frame 27 |
| Student v1 | validity 98, intent 63, date 73, time 92, place 78, full frame 32 |
| Image | `parser:v1` 1.82 GB |
| Local service | 50/50 requests in 23.7 s, 0.47 s/request, 303.6 MiB / 1 GiB |
| HPA | min 1, max 2, CPU 70%, 2 replicas under load |
| Rolling update | v1 → v2 succeeded, header `X-Model-Version: v2`, one transient 502, then 200 |
| Rollback | `kubectl rollout undo` succeeded, header back to v1 |
| Pod delete | replacement 1/1 Running in 11 s |
| Cold start | both pods 1/1 Running in 11 s |
| Load balancing | Ingress served by 2 pods; Locust successes h9wr8 91, 8phn4 37 |
| Load test (Locust, 4 users, 2 min) | 39,463 requests, 39,336 failures (99.68%), 128 success. Errors: 29,196 HTTP 404, 10,138 HTTP 502, 2 HTTP 500. Successful median about 3.7 s. See Limitations. |
| Cost | Per replica ₹3.95/hour (1 CPU × ₹3.50 + 1 GiB × ₹0.45). 2 replicas ₹7.90/hour. Successful rate 3840/hour. Cost per 1000 = ₹2.06. |
| SLO | 95% of `/parse` return 200 within 5 s over 1 hour. Error budget 5%, 192 failed/hour at 3840/hour. **Not met under the Locust run.** |

Scores are percent on `data/validation.jsonl` (100 examples), via `tools/score.py`. Files: `results/base.json`, `results/teacher_validation.json`, `results/student_v1.json`.

## Limitations — read this before reusing the numbers

- **Load test failed.** `/parse` blocks the FastAPI event loop for 1.5–3 s per request (`model.generate` in an async function). With 4 users sending non-stop, health probes timed out, pods restarted during the test, Traefik returned 502 while pods were down and 404 while endpoints were missing. Single sequential requests work (50/50 locally, manual `/parse` via Ingress 200 OK). The fix is to run generation in a threadpool or a separate worker, not to hide the failure.
- **Single node.** One k3s server, one SeaweedFS pod with `emptyDir` storage. Data is lost on pod restart. This is a local demo, not a production setup.
- **Student repeats JSON.** The student was trained without an EOS token after the JSON, so it generates repeated JSON objects. `predict.py` and `service/app.py` extract the first JSON object with `JSONDecoder.raw_decode`.
- **Cold start x1 only.** Only one cold-start run (11 s) was measured. The brief asks for x3 / median.
- **C: disk full once.** On 2026-11-06 the Windows C: drive hit 20 MB free and broke WSL/k3d. Fixed by moving 5 large files to `D:\DownloadsBackup\` (not deleted), C: free rose to 9.4 GB, cluster was recreated clean.

## Teardown

```bash
make down            # k3d cluster delete cs3081
```

## AI use

See `AI_USE.md`. Muse (Meta AI) was used for setup commands, skeleton code, and subnet/NACL design. Every command was run and checked by the student (NACL 6/6, `py_compile`, reading teacher shards, local `/parse` tests). No other student's code, prompt, or report was copied. The friend's submission zip (`230101032.zip`) was used only as a format reference for this README and the repo layout, with all numbers, results, and text above from this student's own runs.

## Report

Full report: `report/report.pdf` (3 pages, under the 8-page limit), source `report/report.md`.
