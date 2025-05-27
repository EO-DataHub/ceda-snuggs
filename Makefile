.PHONY: dockerbuild dockerpush ruff black lint isort pre-commit-check requirements setup
VERSION ?= latest
IMAGENAME = ceda-snuggs
DOCKERREPO ?= public.ecr.aws/eodh

dockerbuild:
	DOCKER_BUILDKIT=1 docker build -t ${IMAGENAME}:${VERSION} .

dockerpush: dockerbuild testdocker
	docker tag ${IMAGENAME}:${VERSION} ${DOCKERREPO}/${IMAGENAME}:${VERSION}
	docker push ${DOCKERREPO}/${IMAGENAME}:${VERSION}

ruff:
	./venv/bin/ruff check .

black:
	./venv/bin/black .

isort:
	./venv/bin/isort . --profile black

lint: ruff black isort validate-pyproject

requirements: requirements.txt

venv:
	virtualenv -p python3.11 venv
	./venv/bin/python -m ensurepip -U
	./venv/bin/pip3 install pip-tools

.make-venv-installed: venv requirements.txt
	./venv/bin/pip3 install -r requirements.txt
	touch .make-venv-installed

.git/hooks/pre-commit:
	./venv/bin/pre-commit install
	curl -o .pre-commit-config.yaml https://raw.githubusercontent.com/EO-DataHub/github-actions/main/.pre-commit-config-python.yaml

setup: venv requirements .make-venv-installed .git/hooks/pre-commit