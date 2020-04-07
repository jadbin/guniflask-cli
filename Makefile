build:
	pip install -e .

test:
	pytest tests

clean:
	@rm -rf build dist *egg-info
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete

.PHONY: build test clean
