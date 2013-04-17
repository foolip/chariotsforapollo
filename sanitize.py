import html5lib
import re
import sys
import xml.dom

src = open(sys.argv[1], 'r')

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
    return next(tags(doc, tagName), None)

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

# remove useless attributes
if body.hasAttribute('bgcolor'):
    body.removeAttribute('bgcolor')
for img in tags(doc, 'img'):
    for attr in ['width', 'height']:
        if img.hasAttribute(attr):
            img.removeAttribute(attr)

# remove comments
for n in walk(doc):
    if n.nodeType == n.COMMENT_NODE:
        remove(n)

# remove the footer (empty elements and images at end of body)
for n in reversed(list(walk(body))):
    if isempty(n):
        if n.nodeType == n.ELEMENT_NODE and n.tagName == 'img':
            if n.getAttribute('src') not in \
                    ['previous.gif', 'next.gif', 'index.gif']:
                break
        remove(n)
    else:
        break

# remove some empty elements
for elm in tags(doc):
    voidTags = set(['br', 'hr', 'img', 'meta'])
    if elm.tagName not in voidTags and isempty(elm):
        assert elm.tagName in ['p']
        remove(elm)

# group figures and their captions
def figurize(fig):
    def nextElement(ref):
        n = ref.nextSibling
        while n and n.nodeType != n.ELEMENT_NODE:
            assert isempty(n)
            n = n.nextSibling
        return n
    imgs = list(tags(fig, 'img'))
    if len(imgs) > 0:
        caption = nextElement(fig)
        if caption.tagName == 'p':
            hr = nextElement(caption)
        else:
            hr = caption
            caption = None
        if hr.tagName == 'hr':
            fig.tagName = 'div'
            fig.setAttribute('class', 'figure')
            if caption != None:
                caption.setAttribute('class', 'caption')
                fig.appendChild(caption)
            remove(hr)
            return True
    return False

for p in tags(doc, 'p'):
    if p.hasAttribute('align') and p.getAttribute('align') == 'center':
        if figurize(p):
            p.removeAttribute('align')

for center in tags(doc, 'center'):
    figurize(center)

# move <a name="foo"> anchors to parent <? id="foo">
for a in tags(doc, 'a'):
    whitelist = set(['p', 'h3'])
    if a.hasAttribute('name') and not a.parentNode.hasAttribute('id') and \
            a.parentNode.tagName in whitelist:
        a.parentNode.setAttribute('id', a.getAttribute('name'))
        while a.firstChild:
            a.parentNode.insertBefore(a.firstChild, a)
        remove(a)

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

# ensure that only whitelisted tags are in the output
for elm in tags(doc):
    tagmap = { 'cite': 'i',
               'em': 'i' }
    if elm.tagName in tagmap:
        elm.tagName = tagmap[elm.tagName]
    whitelist = {'a': ['href'],
                 'b': [], # FIXME
                 'blockquote': [],
                 'body': ['style'],
                 'br': [],
                 'dd': [],
                 'div': ['class'],
                 'dl': [],
                 'dt': [],
                 'h1': [],
                 'h2': [],
                 'h3': ['id'], # FIXME
                 'h4': [], # FIXME
                 'head': [],
                 'hr': [],
                 'html': ['xmlns'],
                 'i': [],
                 'img': ['alt', 'src'],
                 'li': [],
                 'meta': ['content', 'http-equiv'],
                 'ol': [],
                 'p': ['class', 'id', 'style'],
                 'pre': [], # FIXME
                 'style': [],
                 'sup': [],
                 'title': [],
                 'ul': []}
    assert elm.tagName in whitelist
    attrs = elm.attributes
    for i in range(attrs.length):
        attrName = attrs.item(i).name
        try:
            assert attrName in whitelist[elm.tagName]
        except:
            print '%s.%s' % (elm.tagName, attrName)
            assert False

# add the stylesheet
link = doc.createElement('link')
link.setAttribute('rel', 'stylesheet')
link.setAttribute('href', 'stylesheet.css')
style = first('style')
if style != None:
    style.parentNode.insertBefore(link, style)
else:
    first('head').appendChild(link)

dst = open(sys.argv[2], 'w+')
dst.write(html.toxml('utf-8'))
