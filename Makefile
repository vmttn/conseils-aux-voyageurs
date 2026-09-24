IMAGES := $(wildcard monde/*.jpg)

.PHONY: all scrape

all: animation.webp

scrape:
	./scrape.py

animation.webp: $(IMAGES)
	./animate.py
