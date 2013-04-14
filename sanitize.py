#!/usr/bin/env python

import sys

import html5lib

src = open(sys.argv[1], 'r')
dst = open(sys.argv[2], 'w+')

doc = html5lib.parse(src)

dst.write(doc.toxml())
