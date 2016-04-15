import re
import html
from html import unescape
from bs4 import BeautifulSoup
import bs4
import chardet
from lxml import etree
import lxml
from collections import Counter

def tokenize_plain_text(text)->str:
    for tok in text.split():
        tok = tok.strip(' ;,.-"\t\n\':')
        if tok:
            yield tok.lower()

def parse_html_comment(comment):
    """
    IP address is 192.168.2.1, and model is RT-AC68U rev B.
    """
    yield from tokenize_plain_text(comment)
    
def parse_inner_javascript(js):
    raise StopIteration


def parse_html_markup(markup):
    """ Examples:
    <div style="height:100px; width:100%;"></div>
    <script language="JavaScript" type="text/javascript" src="/lang.js">
    <input name="loginUsername" value="">
    <td width="165" height="354" align="center" valign="top" style="border-left-style: none; border-left-width: medium; border-right-style: solid" bordercolor="#4E97B9" bgcolor="#E7DAAC">
    <frame src="Main_Index_HomeGateway.asp" name="folderFrame" marginwidth="0" marginheight="0" noresize>
    """
    tagm = re.search(r'<(\w+)', markup)
    if not tagm:
        raise StopIteration
    tag = tagm.group(1).lower()
    if tag in ['table','tr','td','div','span','p','font','html','head','body', 
            'hr', 'meta']:
        raise StopIteration
    markup = markup[tagm.end()+1:]
    for attrpair in re.findall(r'[\w\-]+\s*=\s*[\w\-/.]+|[\w\-]+\s*=\s*".*?"|[\w-]+', markup):
        try:
            attrname, attrvalue = attrpair.split('=',1)
        except ValueError:
            yield attrpair
            continue
        # events like onmouseover onclick
        attrname = attrname.lower()
        if attrname.startswith('on'):
            continue
        if attrname in ['style','width','height','border'] or \
                'color' in attrname:
            continue
        if attrname not in ['name','value','type','id', 'src','href']:
            yield attrname
        # attribute value
        if attrvalue.startswith('"'):
            attrvalue = unescape(attrvalue.strip('"'))
        if attrvalue.lower().startswith('javascript:'):
            yield from parse_inner_javascript(attrvalue[len('javascript:'):])
        yield from tokenize_plain_text(attrvalue)


def parse_html_javascript(js):
    """
    <script>
    (function () { var old = $.fn.contents; $.fn.contents = function () { try { return old.apply(this, arguments); } catch (e) { return $([]); } } })()
    </script>
    """
    m = re.search(r'<script.*?>', js, re.DOTALL|re.I)
    if not m:
        parse_inner_javascript(js)
    m2 = re.search(r'</script.*?>', js, re.DOTALL|re.I)
    inner_js = js[m.end():m2.start()]
    markup = m.group(0)
    yield from parse_html_markup(markup)
    parse_inner_javascript(inner_js)
 


def parse_html_css(css):
    """
    <style type="text/css">
      body {
        color: purple;
      background-color: #d8da3d }
    </style>
    """
    m = re.search(r'<style.*?>', css, re.DOTALL|re.I)
    m2 = re.search(r'</style.*?>', css, re.DOTALL|re.I)
    style = css[m.end():m2.start()]
    markup = m.group(0)
    yield from parse_html_markup(markup)
    for token in re.findall(r'[\w\-]+', style):
        yield tok.group(0).lower().strip('-')

def parse_html_text(text):
    yield from tokenize_plain_text(text)

def nrepeat(n:int, obj:iter):
    ret = [_ for _ in obj]*n
    for r in ret:
        yield r

def parse_html(htmlcode:str)->str:
    for parag in re.findall(r'<script.*?>.*?</script>|<style.*?>.*?</style>'
            '|<title>.*?</title>|<.+?>|[^<>]+', 
            htmlcode, re.DOTALL|re.IGNORECASE):
        try:
            prefix = parag.lower().split()[0]
        except IndexError:
            continue
        if prefix.startswith('<script'):
            # yield from parse_html_javascript(parag.group(0))
            pass
        elif prefix.startswith('<style'):
            # yield from parse_html_css(parag.group(0))
            pass
        elif prefix.startswith('<title'):
            # upweight title 
            yield 'title'
            yield from nrepeat(3, tokenize_plain_text(unescape(re.sub(r'<.*?>','',parag))))
            yield 'title'
        elif prefix.startswith('<--'):
            # yield from parse_html_comment(unescape(parag))
            pass
        elif prefix.startswith('<'):
            yield from parse_html_markup(parag)
        else:
            yield from tokenize_plain_text(unescape(parag))


def html_unescape_backslash_hex(htmlcode:str)->str:
    r"""
    unescape something like
    <option value="TH">\xE0\xB9\x84\xE0\xB8\x97\xE0\xB8\xA2</option>
    """
    if not re.search(r'\\x[0-9a-fA-F]{2}', htmlcode):
        return htmlcode
    charsets = [_.strip(' "/') for _ in re.findall(r'<meta\ .*charset=(.*?)>', htmlcode, re.I)]
    charsets += ["utf-8", "latin1", "latin2"]

    def backslash_to_bytes(m):
        bs = m.group(0)
        return bytes([int(bs[-2:],16)])
    htmlblob = re.sub(rb'\\x[0-9a-fA-F]{2}', backslash_to_bytes, htmlcode.encode('utf8'))
    for cs in charsets:
        try:
            return htmlblob.decode(cs)
        except (UnicodeDecodeError,LookupError) as ex:
            pass
    pdb.set_trace()
    detres = chardet.detect(htmlblob)
    print("chardet=%s"%(detres))
    return htmlblob.decode(detres['encoding'], errors='ignore')


def get_host(idsession:int, ip_addr:str)->lxml.etree._Element:
    parser = etree.XMLParser(encoding='utf-8', huge_tree=True,recover=True)
    tree = etree.parse('nmaplog/%s.xml'%idsession, parser=parser)
    return tree.xpath(".//address[@addr='%s']/.."%ip_addr)[0]

def get_homepage(host):
    for script in host.xpath(".//script[@id='http-homepage']"):
        try:
            body = script.xpath(".//elem[@key='response_body']")[0].text
        except:
            raise StopIteration
        if body is None:
            raise StopIteration
        yield from parse_html(html_unescape_backslash_hex(body))

def main():
    import sys
    idsession = int(sys.argv[1]) if len(sys.argv)>1 else None
    ipaddr = sys.argv[2] if len(sys.argv)>2 else None
    if idsession is not None:
        host = get_host(idsession, ipaddr)
        tokens = [_.strip() for _ in get_homepage(host) if _.strip()]
    else:
        with open('1069962_WRT1900AC.html','r') as fin:
            htmlcode = fin.read()
        tokens = [_.strip() for _ in parse_html(htmlcode) if _.strip()]
    import pprint
    pp = pprint.PrettyPrinter(width=80, indent=1)
    pp.pprint(tokens)

if __name__=='__main__':
    main()

