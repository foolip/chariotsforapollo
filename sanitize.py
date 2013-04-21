import html5lib
import re
import sys
import xml.dom

mdash = u'\u2014'
lsquo = u'\u2018'
rsquo = u'\u2019'
ldquo = u'\u201C'
rdquo = u'\u201D'
hellip = u'\u2026'

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

# yield all the text node childen of root in tree order
def textnodes(root):
    return (n for n in walk(root) if n.nodeType == n.TEXT_NODE)

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
        return isspace(node.data)
    elif node.nodeType == node.ELEMENT_NODE:
        return all([n.nodeType == n.TEXT_NODE and isspace(n.data)
                    for n in node.childNodes])
    else:
        return False

# equivalent to DOM's textContent
def textContent(node):
    return ''.join([n.data for n in textnodes(node)])

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
        if img.hasAttribute(attr) and not img.getAttribute(attr).endswith('%'):
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

# add [] around note links
for a in tags(doc, 'a'):
    href = a.getAttribute('href')
    if href.startswith('#explanation') or href.startswith('#source'):
        text = textContent(a)
        remove(a.firstChild)
        assert a.firstChild == None
        a.appendChild(doc.createTextNode('[%s]' % text))

# remove useless <b>
for b in tags(doc, 'b'):
    if re.match(r'^\W*$', textContent(b)):
        b.parentNode.replaceChild(b.firstChild, b)
        assert b.firstChild == None
    else:
        # only numbered notes should remain
        assert textContent(b).isdigit() and b.nextSibling.data == '.'

# prettify whitespace
doc.normalize()
for p in tags(doc, 'p'):
    for ref in [p, p.nextSibling]:
        p.parentNode.insertBefore(doc.createTextNode('\n'), ref)
    if p.firstChild.nodeType == p.TEXT_NODE:
        p.firstChild.data = p.firstChild.data.lstrip()
    if p.lastChild.nodeType == p.TEXT_NODE:
        p.lastChild.data = p.lastChild.data.rstrip()
doc.normalize()
for n in textnodes(doc):
    n.data = re.sub(r'\s*\n\s*', '\n', n.data)

# replace ' and " with appropriate left/right single/double quotes
def quotify(elm):
    class State:
        def __init__(this, left, right):
            this.isopen = 'no'
            this.left = left
            this.right = right
        def open(this):
            assert this.isopen in ['no', 'maybe']
            this.isopen = 'yes'
            return this.left
        def close(this):
            assert this.isopen in ['yes', 'maybe']
            this.isopen = 'no'
            return this.right
        def ambclose(this):
            assert this.isopen in ['yes', 'no', 'maybe']
            if this.isopen == 'yes':
                this.isopen = 'maybe'
            return this.right
    sq = State(lsquo, rsquo)
    dq = State(ldquo, rdquo)
    def replace(m):
        q = sq if m.group(0) == "'" else dq
        before = m.string[m.start(0)-1] if m.start(0) > 0 else ' '
        after = m.string[m.end(0)] if m.end(0) < len(m.string) else ' '
        context = before + m.group(0) + after
        # non-quoting and ambiguous usage of '
        if q == sq:
            if before.isalnum() and after.isalpha():
                # moon's or similar
                return rsquo
            if before in 'sz' and after.isspace():
                # engineers' or similar
                return sq.ambclose()
        # the simple cases
        if before.isspace() and not after.isspace():
            return q.open()
        if not before.isspace() and after.isspace():
            return q.close()
        # document-specific cases
        if context[0].isalnum():
            context = 'a' + context[1:]
        if context[2].isalnum():
            context = context[:2] + 'a'
        if context in ['"\'a']:
            return sq.open()
        if context in ['.\'"', ',\'"', "a',"]:
            return sq.close()
        if context in ['("a', '["a']:
            return dq.open()
        if context in ['\'"[', '."[', ',"[', 'a";', '?"[', 'a")', 'a":',
                       'a"[', 'a"]', ')"]', ')":', ')";', '.")', '.";']:
            return dq.close()
        assert False
    # join the text children to do the work ...
    text = textContent(elm)
    text = re.sub(r'[\'"]', replace, text)
    assert sq.isopen in ['no', 'maybe']
    assert dq.isopen in ['no', 'maybe']
    # ... and then spread them out again
    offset = 0
    for n in textnodes(elm):
        n.data = text[offset:offset+len(n.data)]
        offset += len(n.data)

for elm in tags(body):
    if elm.tagName in ['dd', 'h2', 'li', 'p']:
        quotify(elm)

# replace ' - ' with em dash
for n in textnodes(body):
    n.data = re.sub(r'\s+-\s+', mdash, n.data, flags=re.M)

# replace '. . .' with ellipsis
def ellipsify(m):
    s = re.sub(r'\s+', ' ', m.group())
    if s in ['.', '. ']:
        return m.group()
    before = m.string[m.start(0)-1] if m.start(0) > 0 else None
    after = m.string[m.end(0)] if m.end(0) < len(m.string) else None
    quotes = lsquo + rsquo + ldquo + rdquo
    assert before is None or before.isalnum() or before in set(',;?])' + quotes)
    assert after is None or after.isalnum() or after in set(',:?'+ mdash + quotes)
    suffix = '' if (after is None or after in set(',:?' + mdash + rsquo + rdquo)) else ' '
    if s.strip() == '. . .':
        prefix = '' if (before is None or before in set(lsquo + ldquo)) else ' '
        return prefix + hellip + suffix
    elif s.rstrip() == '. . . .':
        assert before.isalpha()
        return '. ' + hellip + suffix
    assert False

for n in textnodes(body):
    n.data = re.sub(r'[\s.]*[.][\s.]*', ellipsify, n.data, flags=re.M)

# assert that the text content is to our liking
text = textContent(body)
assert re.search(r'\s-\s', text, flags=re.M) == None
assert re.search(r'\s'+mdash, text, flags=re.M) == None
assert re.search(mdash+r'\s', text, flags=re.M) == None
assert re.search(r'[\'"]', text) == None

# ensure that only whitelisted tags are in the output
for elm in tags(doc):
    tagmap = { 'cite': 'i',
               'em': 'i' }
    if elm.tagName in tagmap:
        elm.tagName = tagmap[elm.tagName]
    whitelist = {'a': ['href'],
                 'b': [],
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
                 'img': ['alt', 'src', 'width'],
                 'li': [],
                 'meta': ['content', 'http-equiv'],
                 'ol': [],
                 'p': ['class', 'id', 'style'],
                 'pre': [], # FIXME
                 'span': [],
                 'style': ['type'],
                 'sup': [],
                 'title': [],
                 'ul': []}
    assert elm.tagName in whitelist
    attrs = elm.attributes
    for i in range(attrs.length):
        attrName = attrs.item(i).name
        assert attrName in whitelist[elm.tagName]

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
