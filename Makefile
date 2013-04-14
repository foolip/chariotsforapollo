default: chariotsforapollo.epub

clean:
	git clean -fX

# for simplicity, depend on all files known to Git
GIT_FILES := $(shell git ls-tree -r --name-only HEAD)

# extract OEBPS dependencies from content.opf
OEBPS_FILES := $(addprefix OEBPS/, $(shell grep '<item href' OEBPS/content.opf | cut -d '"' -f 2))

chariotsforapollo.epub: $(GIT_FILES) $(OEBPS_FILES)
	zip -X $@ mimetype
	zip -rg $@ META-INF OEBPS -x \*~ \*.gitignore

OEBPS/%.html: %.html
	PYTHONPATH=html5lib-python python sanitize.py $< $@

OEBPS/%.jpg: %.jpg
	cp $< $@
