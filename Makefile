default: chariotsforapollo.epub

clean:
	git clean -fX

# for simplicity, depend on all files known to Git
GIT_FILES := $(shell git ls-tree -r --name-only HEAD)

chariotsforapollo.epub: $(GIT_FILES) OEBPS/cover.jpg
	zip -X $@ mimetype
	zip -rg $@ META-INF OEBPS -x \*~ \*.gitignore

OEBPS/%.jpg: %.jpg
	cp $< $@
