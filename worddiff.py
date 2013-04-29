#!/usr/bin/env python
#
# Diff the words of two files, ignoring whitespace.
# Get words from HTML by including worddiff.js

import difflib
import os.path
import sys

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]),
                             'html5lib-python'))
import html5lib

def getwords(path):
    f = open(path, 'r')
    if path.endswith('.htm') or path.endswith('.html'):
        doc = html5lib.parse(f, treebuilder='dom')
        body = doc.documentElement.lastChild
        assert body.tagName == 'body'
        return ''.join(itertext(body)).encode('utf-8').split()
    else:
        return f.read().split()

def itertext(node):
    if node.nodeType == node.TEXT_NODE:
        yield node.data.replace(u'\u00AD', '')
    elif node.nodeType == node.ELEMENT_NODE:
        showTag = node.tagName in ['b', 'i', 'sub', 'sup']
        if showTag:
            yield '<%s>' % node.tagName
        for child in node.childNodes:
            for text in itertext(child):
                yield text
        if showTag:
            yield '</%s>' % node.tagName

a = getwords(sys.argv[1])
b = getwords(sys.argv[2])

diff = difflib.unified_diff(a, b, n=25, lineterm='',
                            fromfile=sys.argv[1],
                            tofile=sys.argv[2])

context = None
words = []

def printwords():
    if context is None:
        return
    sys.stdout.write({'-': '\033[91m',
                      '+': '\033[92m'}.get(context, ''))
    sys.stdout.write(context)
    sys.stdout.write(' '.join(words))
    if context in '+-':
        sys.stdout.write('\033[0m')
    sys.stdout.write('\n')

for line in diff:
    word = line[1:]
    if context is line[0]:
        words.append(word)
    else:
        printwords()
        context = line[0]
        words = [word]

printwords()
