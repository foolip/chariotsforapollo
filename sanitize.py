import html5lib
import re
import sys
import xml.dom

src = open(sys.argv[1], 'r')
dst = open(sys.argv[2], 'w+')

doc = html5lib.parse(src, treebuilder='dom')

# yield all the children of root in tree order
def walk(root):
    pending = list(reversed(root.childNodes))
    while len(pending) > 0:
        node = pending.pop()
        yield node
        for child in reversed(node.childNodes):
            pending.append(child)

# yield all the element childen of root in tree order
def tags(root, tagName=None):
    return (n for n in walk(root) if n.nodeType == n.ELEMENT_NODE and
            (tagName == None or n.tagName == tagName))

# return the first element matching tagName
def first(tagName):
    return next(tags(doc, tagName))

# remove an element from its parent
def remove(node):
    node.parentNode.removeChild(node)

# true if node is whitespace or has only whitespace children
def isempty(node):
    def isspace(s):
        return len(s) == 0 or s.isspace()
    if node.nodeType == node.TEXT_NODE:
        return isspace(node.nodeValue)
    elif node.nodeType == node.ELEMENT_NODE:
        return all([n.nodeType == n.TEXT_NODE and isspace(n.nodeValue)
                    for n in node.childNodes])
    else:
        return False

html = doc.documentElement
body = first('body')

# add XHTML talismans
html.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml')
first('meta').setAttribute('content', 'application/xhtml+xml; charset=utf-8')

# remove obsolete attributes
body.removeAttribute('bgcolor')

# remove comments
for n in walk(doc):
    if n.nodeType == n.COMMENT_NODE:
        remove(n)

# remove the footer (empty elements at end of body)
for n in reversed(list(walk(body))):
    if isempty(n):
        if n.nodeType == n.ELEMENT_NODE and n.tagName == 'img':
            assert n.getAttribute('src') in \
                ['previous.gif', 'next.gif', 'index.gif']
        remove(n)
    else:
        break

# remove some empty elements
for elm in tags(doc):
    voidTags = set(['br', 'hr', 'img', 'meta'])
    if elm.tagName not in voidTags and isempty(elm):
        assert elm.tagName in ['p']
        remove(elm)

# prettify whitespace
doc.normalize()
for p in tags(doc, 'p'):
    for ref in [p, p.nextSibling]:
        p.parentNode.insertBefore(doc.createTextNode('\n'), ref)
    if p.firstChild.nodeType == p.TEXT_NODE:
        p.firstChild.nodeValue = p.firstChild.nodeValue.lstrip()
    if p.lastChild.nodeType == p.TEXT_NODE:
        p.lastChild.nodeValue = p.lastChild.nodeValue.rstrip()
doc.normalize()
for n in walk(doc):
    if n.nodeType == n.TEXT_NODE:
        n.nodeValue = re.sub(r'\s*\n\s*', '\n', n.nodeValue)

dst.write(html.toxml())
