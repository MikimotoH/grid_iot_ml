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
        tok = tok.strip(' ;,.-"\t\n\'')
        if tok:
            yield tok.lower()

def parse_html_comment(comment):
    """
    IP address is 192.168.2.1, and model is RT-AC68U rev B.
    """
    # for token in re.finditer(r'[0-9A-Z_\-\.]+', comment, re.DOTALL|re.IGNORECASE):
    #     yield token.group(0).lower().strip('.')
    yield from tokenize_plain_text(comment)
    
 
def parse_html_markup(markup):
    """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <div style="height:100px; width:100%;">
    </div>
    <script language="JavaScript" type="text/javascript" src="/lang.js">
    """
    for tok in re.finditer(r'[0-9a-z]+', markup, re.DOTALL|re.I):
        yield tok.group(0).lower()

def parse_html_javascript(js):
    """
    <script>
    (function () { var old = $.fn.contents; $.fn.contents = function () { try { return old.apply(this, arguments); } catch (e) { return $([]); } } })()
    </script>
    """
    m = re.search(r'<script.*?>', js, re.DOTALL|re.I)
    m2 = re.search(r'</script.*?>', js, re.DOTALL|re.I)
    script = js[m.end():m2.start()]
    markup = m.group(0)
    yield from parse_html_markup(markup)
    for token in re.finditer(r'[0-9a-z_]+', script, re.DOTALL|re.I):
        yield token.group(0)

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
    for tok in re.finditer(r'[0-9a-z\-]+', style, re.DOTALL|re.I):
        yield tok.group(0).lower().strip('-')

def parse_html_text(text):
    yield from tokenize_plain_text(text)

re.search(r'(?<=\>).+(?=\<)', '<em> a b c </em>').group(0)

def parse_html(htmlcode:str)->str:
    for parag in re.finditer(r'<script.*?>.*?</script>|<style.*?>.*?</style>|<.+?>|(?<=\>)[^<>]+(?=\<)', htmlcode, re.DOTALL|re.IGNORECASE):
        prefix,*_ = parag.group(0).lower().split(' ',1)
        if prefix.startswith('<script'):
            # yield from parse_html_javascript(parag.group(0))
            pass
        elif prefix.startswith('<style'):
            # yield from parse_html_css(parag.group(0))
            pass
        elif prefix.startswith('<--'):
            yield from parse_html_comment(unescape(parag.group(0)))
        elif prefix.startswith('<'):
            yield from parse_html_markup(parag.group(0))
        else:
            yield from parse_html_text(unescape(parag.group(0)))

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
        body = script.xpath(".//elem[@key='response_body']")[0].text
        yield from parse_html(html_unescape_backslash_hex(body))

def main1():
    host = get_host(577844, '192.168.2.1')
    tokens = [_.strip() for _ in get_homepage(host) if _.strip()]
    counter = Counter(tokens)
    import pprint
    pp = pprint.PrettyPrinter(width=80, indent=1)
    pp.pprint(counter)
def main():
    with open('1069962_WRT1900AC.html','r') as fin:
        htmlcode = fin.read()
    tokens = [_.strip() for _ in parse_html(htmlcode) if _.strip()]
    counter = Counter(tokens)
    import pprint
    pp = pprint.PrettyPrinter(width=80, indent=1)
    pp.pprint(counter)

if __name__=='__main__':
    main()

