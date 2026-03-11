IMAGES := $(wildcard monde/*.jpg)

.PHONY: all scrape

all: animation.gif optimized.gif

scrape:
	./scrape.py

animation.gif: $(IMAGES)
	./make_gif.py

optimized.gif: animation.gif
	gifsicle --optimize=3 --lossy=33 --output optimized.gif animation.gif