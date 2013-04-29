#!/usr/bin/env python
#
# Diff the words of two files, ignoring whitespace.
# Get words from HTML by including worddiff.js

import difflib
import sys

def getwords(path):
    return open(path, 'r').read().split()

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
