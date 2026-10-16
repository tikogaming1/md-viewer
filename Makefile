# MD Viewer - Bauen, Testen, Paketieren
#
#   make            Hilft weiter (wie "make help")
#   make deps       Node-Abhaengigkeiten installieren
#   make build      Fremd-Assets + Web-Bundle bauen
#   make test       Alle Tests (Python + JavaScript)
#   make deb        .deb-Paket nach release/ bauen
#
# Voraussetzungen fuer "make deb": python3, node/npm, dpkg-deb, ImageMagick
# (nur fuer die Icons; das SVG genuegt sonst auch).

SHELL := /bin/sh
PYTHON ?= python3
NPM ?= npm
VERSION := $(shell sed -n 's/^__version__ = "\(.*\)"/\1/p' src/mdviewer/__init__.py)
PKG := md-viewer
DEB := release/$(PKG)_$(VERSION)_all.deb

.PHONY: help all deps build bundle vendor test test-python test-js icons check-install deb clean clean-all install run

help:
	@echo "MD Viewer $(VERSION)"
	@echo ""
	@echo "  make deps            Node-Abhaengigkeiten installieren (npm install)"
	@echo "  make build           Web-Assets und Bundle bauen (npm run build)"
	@echo "  make test            Alle Tests ausfuehren"
	@echo "  make icons           App-Icons neu erzeugen"
	@echo "  make deb             Debian-Paket bauen -> $(DEB)"
	@echo "  make run             App aus dem Quelltext starten"
	@echo "  make clean           Baureste entfernen"
	@echo "  make clean-all       Zusaetzlich node_modules und release/ entfernen"

all: deb

deps:
	$(NPM) install --no-audit --no-fund

vendor: deps
	$(NPM) run vendor

bundle:
	$(NPM) run bundle

build: vendor bundle

test: test-python test-js

test-python:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests/python -t tests/python -p 'test_*.py' -v

test-js: bundle
	$(NPM) run test

test-js-src:
	node --test "tests/js/*.test.mjs"

icons:
	$(PYTHON) scripts/make_icons.py

check-install: $(DEB)
	dpkg-deb --info $(DEB)
	dpkg-deb --contents $(DEB) | head -40
	@echo ""
	@echo "Lintian-Hinweis: 'lintian $(DEB)' zeigt weitere Details."

deb: build icons
	$(PYTHON) scripts/build-deb.py
	@echo "Fertig: $(DEB)"
	@echo "Installieren:  sudo apt install ./$(DEB)"
	@echo "Entfernen:     sudo apt remove $(PKG)"

run: build
	PYTHONPATH=src $(PYTHON) -m mdviewer

install: $(DEB)
	sudo apt install ./$(DEB)

clean:
	rm -rf packaging/.stage release/$(PKG)_*_all.deb *.deb

clean-all: clean
	rm -rf node_modules release web/bundle web/vendor
