IMAGES := $(wildcard monde/*.jpg)

.PHONY: all scrape site serve

all: animation.webp

scrape:
	./scrape.py

site:
	./build_site.py

serve: site
	@echo "http://localhost:8000/"
	python3 -m http.server 8000 -d _site

animation.webp: $(IMAGES)
	./animate.py
