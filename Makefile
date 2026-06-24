.PHONY: install config-check

install:
	pip install -r requirements.txt

config-check:
	PYTHONPATH=src python -c "from exoscan.config import load_config; c = load_config(); c.ensure_directories(); print('Config OK:', c.project.name)"
