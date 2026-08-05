.PHONY: test readiness live upstream
test:
	python3 -m pytest -q
readiness:
	./scripts/readiness.py
live:
	./scripts/run-live.sh
upstream:
	./scripts/bootstrap-upstream.sh git-submodule
