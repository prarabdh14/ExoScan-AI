.PHONY: install config-check download-catalogs build-labels phase1

install:
	pip install -r requirements.txt

config-check:
	PYTHONPATH=src python -c "from exoscan.config import load_config; c = load_config(); c.ensure_directories(); print('Config OK:', c.project.name)"

download-catalogs:
	PYTHONPATH=src python scripts/download_catalogs.py

build-labels:
	PYTHONPATH=src python scripts/build_training_labels.py

phase1: download-catalogs build-labels
