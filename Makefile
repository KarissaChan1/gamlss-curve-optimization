# Read version from pyproject.toml
VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)

# Docker image name
IMAGE_NAME := karissachan1/tiny-curvy-brains

.PHONY: build push test run

build:
	@echo "Building Docker image with version $(VERSION)"
	docker build -t $(IMAGE_NAME):$(VERSION) -t $(IMAGE_NAME):latest .

push:
	docker push $(IMAGE_NAME):$(VERSION)
	docker push $(IMAGE_NAME):latest

test:
	poetry run pytest -s

# Example run command with test data
run:
	docker run -v $(PWD)/tests/data:/app/data -v $(PWD)/output:/app/output \
		$(IMAGE_NAME):latest growth_curves \
		-i /app/data/HSC_Normals_Biomarkers_FINAL.xlsx \
		-a Age_yrs_ \
		-b Intensity \
		-s /app/output \
		-d NAWM ED 