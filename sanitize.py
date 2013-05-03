#!/usr/bin/env python

import os.path
import re
import sys
import xml.dom

sys.path.append(os.path.join(os.path.dirname(sys.argv[0]),
                             'html5lib-python'))
import html5lib

mdash = u'\u2014'
lsquo = u'\u2018'
rsquo = u'\u2019'
ldquo = u'\u201C'
rdquo = u'\u201D'
hellip = u'\u2026'

srcpath = sys.argv[1]
dstpath = sys.argv[2]

# parse into a DOM (fail on error)
def parse(path):
    p = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder('dom'))
    src = open(path, 'r')
    doc = p.parse(src)
    if len(p.errors) > 0:
        for pos, errorcode, datavars in p.errors:
            msg = html5lib.constants.E.get(errorcode, 'Unknown error "%s"' %
                                           errorcode) % datavars
            sys.stderr.write('%s:%d:%d: error: %s\n' %
                             (path, pos[0], pos[1], msg))
        sys.exit(len(p.errors))
    return doc

# doc is global, for everyone's convenience
doc = parse(srcpath)
doc.normalize()

# yield all the children of root in tree order
def iterNodes(root, exclude=None):
    pending = list(reversed(root.childNodes))
    while len(pending) > 0:
        node = pending.pop()
        if exclude and exclude(node):
            continue
        yield node
        for child in reversed(node.childNodes):
            pending.append(child)

# yield all the element childen of root in tree order
def iterTags(root, tagName=None):
    return (n for n in iterNodes(root) if n.nodeType == n.ELEMENT_NODE and
            (tagName == None or n.tagName == tagName))

# yield all the text node childen of root in tree order
def iterText(root, exclude=None):
    return (n for n in iterNodes(root, exclude) if n.nodeType == n.TEXT_NODE)

# add a stylesheet (before any <style> elements)
def addStylesheet(href):
    link = doc.createElement('link')
    link.setAttribute('rel', 'stylesheet')
    link.setAttribute('href', href)
    style = first('style')
    if style:
        insertBefore(link, style)
        insertBefore(doc.createTextNode('\n'), style)
    else:
        first('head').appendChild(link)

# add XHTML talismans
def addTalismans():
    first('html').setAttribute('xmlns', 'http://www.w3.org/1999/xhtml')
    first('meta').setAttribute('content',
                               'application/xhtml+xml; charset=utf-8')

# verify that brackets are balanced
def checkBrackets(elm):
    def error(bracket, line):
        sys.stderr.write('%s: error: Unbalanced bracket: %s\n' %
                         (srcpath, bracket))
        sys.stderr.write('%s\n' % line.strip())
        sys.exit(1)

    stack = []
    groups = ['[]', '()', '{}', '<>']
    for line in textContent(elm).splitlines():
        for c in line:
            for group in groups:
                if c == group[0]:
                    # opening bracket
                    stack.append((c, line))
                elif c == group[1]:
                    # closing bracket
                    if len(stack) > 0:
                        if stack[-1][0] == group[0]:
                            stack.pop()
                        else:
                            error(*stack[-1])
                    else:
                        error(c, line)
    if len(stack) > 0:
        error(*stack[0])

# check that there no non-void empty elements
def checkPolyglot():
    voidTags = set(['area', 'base', 'br', 'col', 'embed', 'hr',
                    'img', 'input', 'keygen', 'link', 'menuitem',
                    'meta', 'param', 'source', 'track', 'wbr'])
    doc.normalize()
    for elm in iterTags(doc):
        if len(elm.childNodes) == 0 and elm.tagName not in voidTags:
            sys.stderr.write('%s: error: <%s/> will parse differently as HTML and XML\n' %
                             (srcpath, elm.tagName))
            sys.exit(1)

# collapse newlines (also strips leading/trailing whitespace)
def collapseNewlines():
    doc.normalize()
    for n in iterText(doc):
        n.data = re.sub(r'\s*\n\s*', '\n', n.data)

# replace ' - ' with em dash
def dashify(elm):
    for n in iterText(elm):
        n.data = re.sub(r'\s+-\s+', mdash, n.data, flags=re.M)
    # fail if the input was too complicated for us
    text = textContent(elm)
    assert re.search(r'\s-\s', text, flags=re.M) == None
    assert re.search(r'\s'+mdash, text, flags=re.M) == None
    assert re.search(mdash+r'\s', text, flags=re.M) == None

# replace '. . .' with ellipsis
def ellipsify(elm):
    def repl(m):
        s = re.sub(r'\s+', ' ', m.group())
        if s in ['.', '. ']:
            return m.group()
        before = m.string[m.start(0)-1] if m.start(0) > 0 else None
        after = m.string[m.end(0)] if m.end(0) < len(m.string) else None
        quotes = lsquo + rsquo + ldquo + rdquo
        assert before is None or before.isalnum() or \
            before in set(',;?])' + quotes)
        assert after is None or after.isalnum() or \
            after in set(',;:?'+ mdash + quotes)
        suffix = '' if (after is None or after in
                        set(',;:?' + mdash + rsquo + rdquo)) else ' '
        if s.strip() == '. . .':
            prefix = '' if (before is None or before in
                            set(lsquo + ldquo)) else ' '
            return prefix + hellip + suffix
        elif s.rstrip() == '. . . .':
            assert before.isalpha()
            return '. ' + hellip + suffix
        assert False
    for n in iterText(elm):
        n.data = re.sub(r'[\s.]*[.][\s.]*', repl, n.data, flags=re.M)

# strip internal whitespace and pad with newlines
def externalizeWhitespace(tagNames):
    doc.normalize()
    for elm in iterTags(doc):
        if elm.tagName not in tagNames:
            continue
        if elm.firstChild.nodeType == elm.TEXT_NODE:
            elm.firstChild.data = elm.firstChild.data.lstrip()
        if elm.lastChild.nodeType == elm.TEXT_NODE:
            elm.lastChild.data = elm.lastChild.data.rstrip()
        pad(elm, '\n')

# return the first element matching tagName
def first(tagName):
    return next(iterTags(doc, tagName), None)

# return the last element matching tagName
def last(tagName):
    ret = None
    for elm in iterTags(doc, tagName):
        ret = elm
    return ret

# insert elm after ref
def insertBefore(elm, ref):
    ref.parentNode.insertBefore(elm, ref)

# insert elm after ref
def insertAfter(elm, ref):
    ref.parentNode.insertBefore(elm, ref.nextSibling)

# true if node is whitespace or has only whitespace children
def isEmpty(node):
    def isSpace(s):
        return len(s) == 0 or s.isspace()
    if node.nodeType == node.TEXT_NODE:
        return isSpace(node.data)
    elif node.nodeType == node.ELEMENT_NODE:
        return all([n.nodeType == n.TEXT_NODE and isSpace(n.data)
                    for n in node.childNodes])
    else:
        return False

# change element names based on a map like { 'em' : 'i' }
def mapTags(tagMap):
    for elm in iterTags(doc):
        if elm.tagName in tagMap:
            elm.tagName = tagMap[elm.tagName]

# pad element with char, if it's not already there
def pad(elm, char):
    prev = elm.previousSibling
    if prev and prev.nodeType == elm.TEXT_NODE:
        if not prev.data.endswith(char):
            prev.data = prev.data + char
    else:
        insertBefore(doc.createTextNode(char), elm)
    next = elm.nextSibling
    if next and next.nodeType == elm.TEXT_NODE:
        if not next.data.startswith(char):
            next.data = char + next.data
    else:
        insertAfter(doc.createTextNode(char), elm)

# move direct text children and their friends into <p>
def paragraphize(elm):
    p = None
    for n in list(elm.childNodes):
        create = False
        append = False
        if n.nodeType == n.TEXT_NODE:
            create = not isEmpty(n)
            append = True
        elif n.nodeType == n.ELEMENT_NODE:
            if n.tagName in ['a', 'b', 'i', 'span', 'sub', 'sup']:
                create = True
                append = True
            else:
                assert n.tagName in ['blockquote', 'center', 'div', 'dl',
                                     'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                     'hr', 'ol', 'p', 'table', 'ul']
                p = None
        else:
            assert False
        if create and p == None:
            p = doc.createElement('p')
            replace(n, p)
        if append and p != None:
            p.appendChild(n)

# make URLs as relative as possible
# path is the (rightmost) bit which should be stripped
def relativize(path):
    for a in iterTags(doc, 'a'):
        if a.hasAttribute('href'):
            href = a.getAttribute('href')
            # strip leading parts of the path
            href = href.split(path)[-1]
            # strip the filename from local #references
            filename = srcpath.split('/')[-1]
            if href.startswith(filename + '#'):
                href = href[len(filename):]
            # done
            a.setAttribute('href', href)

# remove an element from its parent
def remove(node):
    node.parentNode.removeChild(node)

# remove attributes based on a map like { 'body' : [bgcolor] }
def removeAttributes(attrMap):
    for elm in iterTags(doc):
        if elm.tagName in attrMap:
            for attr in attrMap[elm.tagName]:
                if elm.hasAttribute(attr):
                    elm.removeAttribute(attr)

# remove all comment nodes
def removeComments():
    for n in iterNodes(doc):
        if n.nodeType == n.COMMENT_NODE:
            remove(n)

# remove empty elements
def removeEmpty(tagNames):
    # reverse order to get them all
    for elm in reversed(list(iterTags(doc))):
        if elm.tagName in tagNames and isEmpty(elm):
            remove(elm)

# remove junk <meta> tags
def removeMeta():
    kept = 0
    for meta in iterTags(doc, 'meta'):
        if meta.hasAttribute('http-equiv'):
            kept += 1
        else:
            remove(meta)
    assert kept == 1

# replace oldElm with newElm
def replace(oldElm, newElm):
    oldElm.parentNode.replaceChild(newElm, oldElm)

# replace an element with its children
def replaceWithChildren(elm):
    while elm.firstChild:
        insertBefore(elm.firstChild, elm)
    remove(elm)

# serialize as XHTML
def serialize(path):
    dst = open(path, 'w+')
    dst.write(doc.documentElement.toxml('utf-8'))
    dst.write('\n')
    dst.close()

# equivalent to DOM's textContent
def textContent(node):
    return ''.join([n.data for n in iterText(node)])

# replace ' and " with appropriate left/right single/double quotes
def quotify(elm, exclude=None):
    def error(msg):
        sys.stderr.write('%s: error: %s\n' % (srcpath, msg))
        sys.stderr.write(text)
        sys.exit(1)

    class State:
        def __init__(this, left, right):
            this.isopen = 'no'
            this.left = left
            this.right = right
        def open(this):
            if this.isopen == 'yes':
                error('Right quote (%s) missing' % this.right)
            this.isopen = 'yes'
            return this.left
        def close(this):
            if this.isopen == 'no':
                error('Left quote (%s) missing' % this.left)
            this.isopen = 'no'
            return this.right
        def ambclose(this):
            if this.isopen == 'yes':
                this.isopen = 'maybe'
            return this.right
    sq = State(lsquo, rsquo)
    dq = State(ldquo, rdquo)

    def repl(m):
        q = dq if m.group(0) == '"' else sq
        before = m.string[m.start(0)-1] if m.start(0) > 0 else ' '
        after = m.string[m.end(0)] if m.end(0) < len(m.string) else ' '

        def isWord(c):
            assert len(c) == 1
            return bool(re.match(r'\w', c, re.U))

        # non-quoting and ambiguous usage of '
        if m.group() == "'":
            if isWord(before) and isWord(after):
                # moon's or similar
                return rsquo
            if before in 'sz' and after.isspace():
                # engineers' or similar
                return sq.ambclose()

        # cases with whitespace on either side
        if before.isspace() and not after.isspace():
            return q.open()
        if not before.isspace() and after.isspace():
            return q.close()

        # cases with no whitespace
        canOpen = isWord(after) or after in set ('[(' + hellip)
        canClose = isWord(before) or before in set('.,;!?)]' + hellip)
        if canOpen and not canClose:
            return q.open()
        if canClose and not canOpen:
            return q.close()

        error('Quote (%s) needs manual intervention' % m.group(0))

    # join the text children to do the work ...
    textNodes = list(iterText(elm, exclude))
    text = ''.join([n.data for n in textNodes])
    text = re.sub(r'[`\'"]', repl, text)

    if sq.isopen == 'yes':
        error('Right quote (%s) missing' % sq.right)
    if dq.isopen == 'yes':
        error('Right quote (%s) missing' % dq.right)

    # ... and then spread them out again
    offset = 0
    for n in textNodes:
        n.data = text[offset:offset+len(n.data)]
        offset += len(n.data)

# sanitize away!

body = first('body')

removeAttributes({'body': ['bgcolor'],
                  'img': ['align', 'height', 'hspace', 'vspace', 'width']})

removeComments()

mapTags({'cite': 'i', 'em': 'i', 'strong': 'b'})

removeEmpty(['b', 'i', 'li', 'p', 'sub', 'sup'])

removeMeta()

# remove the footer (empty elements and images at end of body)
for n in reversed(list(iterNodes(body))):
    if isEmpty(n):
        if n.nodeType == n.ELEMENT_NODE and n.tagName == 'img':
            if n.getAttribute('src') not in \
                    ['previous.gif', 'next.gif', 'index.gif']:
                break
        remove(n)
    else:
        break

# group figures and their captions
def figurize(fig):
    def nextElement(ref):
        n = ref.nextSibling
        while n and n.nodeType != n.ELEMENT_NODE:
            assert isEmpty(n)
            n = n.nextSibling
        return n
    imgs = list(iterTags(fig, 'img'))
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

for p in iterTags(doc, 'p'):
    if p.hasAttribute('align') and p.getAttribute('align') == 'center':
        if figurize(p):
            p.removeAttribute('align')

for center in iterTags(doc, 'center'):
    figurize(center)

# assert that all images were properly converted
for img in iterTags(doc, 'img'):
    if img.getAttribute('src') != 'cover.jpg':
        fig = img.parentNode
        assert fig.getAttribute('class') == 'figure'

# move <a name="foo"> anchors to parent <? id="foo">
for a in iterTags(doc, 'a'):
    whitelist = set(['p', 'h3'])
    if a.hasAttribute('name') and not a.parentNode.hasAttribute('id') and \
            a.parentNode.tagName in whitelist:
        a.parentNode.setAttribute('id', a.getAttribute('name'))
        replaceWithChildren(a)

# add [] around note links (and remember them for quotify)
noteLinks = set()
for a in iterTags(doc, 'a'):
    href = a.getAttribute('href')
    if href.startswith('#explanation') or href.startswith('#source'):
        text = textContent(a)
        remove(a.firstChild)
        assert a.firstChild == None
        a.appendChild(doc.createTextNode('[%s]' % text))
        noteLinks.add(a)

# remove useless <b>
for b in iterTags(doc, 'b'):
    if re.match(r'^\W*$', textContent(b)):
        b.parentNode.replaceChild(b.firstChild, b)
        assert b.firstChild == None
    else:
        # only numbered notes should remain
        assert textContent(b).isdigit() and b.nextSibling.data == '.'

for elm in iterTags(body):
    if elm.tagName in ['dd', 'dt', 'h1', 'h2', 'h3', 'li', 'p', 'td', 'th']:
        quotify(elm, lambda n: n in noteLinks)
assert re.search(r'[`\'"]', textContent(body)) == None

if srcpath != 'ch11-6.html':
    for elm in iterTags(body):
        if elm.tagName in ['dd', 'dt', 'h1', 'h2', 'h3', 'li', 'p', 'td', 'th']:
            checkBrackets(elm)
checkBrackets(body)

dashify(body)

ellipsify(body)

externalizeWhitespace(['dd', 'dt', 'li', 'p'])

collapseNewlines()

addTalismans()

addStylesheet('stylesheet.css')

checkPolyglot()

serialize(dstpath)
