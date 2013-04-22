default: chariotsforapollo.epub

.PHONY: clean
clean:
	git clean -fX

# for simplicity, depend on all files known to Git
GIT_FILES := $(shell git ls-tree -r --name-only HEAD)

# extract OEBPS dependencies from content.opf
OEBPS_FILES := $(addprefix OEBPS/, $(shell grep '<item href' OEBPS/content.opf | cut -d '"' -f 2))

chariotsforapollo.epub: $(GIT_FILES) $(OEBPS_FILES)
	rm -f $@
	zip -X $@ mimetype
	zip -rg $@ META-INF OEBPS -x \*~ \*.gitignore

OEBPS/%.html: %.html
	PYTHONPATH=html5lib-python python sanitize.py $< $@

OEBPS/images/%: images/%
	./resize.sh $< $@ 1000 1000

OEBPS/%.gif: %.gif
	./resize.sh $< $@ 1000 1000

OEBPS/%.jpg: %.jpg
	cp $< $@

.PHONY: validate
validate: chariotsforapollo.epub
	java -jar epubcheck/epubcheck-3.0.jar $<
