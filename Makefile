SUBSET ?= 0
OUT ?= models/v1
up:
	k3d cluster create --config cluster/k3d.yaml || true
	kubectl apply -f k8s/00-namespaces.yaml
	kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/ingress.yaml -f k8s/hpa.yaml
down:
	k3d cluster delete cs3081 || true
train:
	.venv/bin/python training/train.py $(SUBSET)
clean:
	python3 worker/clean.py
test:
	.venv/bin/python -m pytest tests -q
