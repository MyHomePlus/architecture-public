PYTHON ?= python3

.PHONY: render render-local check clean

render:
	$(PYTHON) scripts/render.py

# 需要 Java + PlantUML jar；PLANTUML_JAR=/path/plantuml.jar make render-local
render-local:
	$(PYTHON) scripts/render.py --backend local

check:
	$(PYTHON) scripts/render.py --check

clean:
	rm -rf build
