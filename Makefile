EPUB_FILE := example.epub

default: $(EPUB_FILE)

# for simplicity, depend on all files known to Git
GIT_FILES := $(shell git ls-tree -r --name-only HEAD)

# extract OEBPS dependencies from content.opf
OEBPS_FILES := $(addprefix OEBPS/, $(shell grep '<item href' OEBPS/content.opf | cut -d '"' -f 2))

$(EPUB_FILE): $(GIT_FILES) $(OEBPS_FILES)
	rm -f $@
	zip -X $@ mimetype
	zip -rg $@ META-INF OEBPS -x \*~ \*.gitignore

OEBPS/%.htm: %.htm
	PYTHONPATH=html5lib-python python sanitize.py $< $@

OEBPS/%.html: %.html
	PYTHONPATH=html5lib-python python sanitize.py $< $@

OEBPS/%.gif: %.gif
	cp $< $@

OEBPS/%.jpg: %.jpg
	cp $< $@

OEBPS/stylesheet.css: stylesheet.css
	cp $< $@

.PHONY: clean
clean:
	git clean -fX

.PHONY: validate
validate: $(EPUB_FILE)
	java -jar epubcheck/epubcheck-3.0.jar $<
