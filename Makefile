.PHONY: install-infra synth deploy diff test
install-infra:
	python3 -m venv .venv && . .venv/bin/activate && pip install -r infra/requirements.txt
synth:
	. .venv/bin/activate && cdk synth
diff:
	. .venv/bin/activate && cdk diff
deploy:
	. .venv/bin/activate && cdk deploy
