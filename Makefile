.PHONY: all test check flow check-drift clean

all: test check

test:
	pytest

check:
	python scripts/check.py

flow:
	python scripts/generate_flow.py

check-drift:
	python scripts/generate_flow.py --check-drift
