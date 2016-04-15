#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import re
import traceback
import pdb
from lxml import etree
from lxml import etree
from lxml.etree import ElementTree
from bs4 import BeautifulSoup
import lxml
from html import unescape
from lxml import objectify
from parse_html import parse_html, html_unescape_backslash_hex, nrepeat
from parse_html import tokenize_plain_text
from parse_html import get_host
from bs4 import BeautifulSoup
import traceback
import pdb


def lxml_remove_namespace(xml_tree:lxml.etree.ElementTree):
    root = xml_tree.getroot()
    for elem in root.getiterator():
        if not hasattr(elem.tag, 'find'): continue
        i = elem.tag.find('}')
        if i >= 0:
            elem.tag = elem.tag[i+1:]
    objectify.deannotate(root, cleanup_namespaces=True)
    return root


def parse_response_header(header:lxml.etree.ElementTree)->str:
    for child in header.getchildren():
        if not child.text:
            continue
        text = child.text
        try:
            fieldname, fieldvalue = text.split(': ', maxsplit=1)
        except ValueError:
            continue
        fieldname = fieldname.lower() 
        # From RFC 2616 - "Hypertext Transfer Protocol -- HTTP/1.1", Section 4.2, "Message Headers":
        #    Field names are case-insensitive.
        if fieldname in ['content-length', 'date', 'last-modified', 
                'connection', 'content-type', 'cache-control', 'pragma', 
                'transfer-encoding','etag','accept-encoding','accept-ranges']:
            continue
        if fieldname=='www-authenticate':
            try:
                realm = re.search(r'realm="(.*)"', fieldvalue, re.I).group(1)
                yield from nrepeat(3, tokenize_plain_text(realm))
            except AttributeError:
                pass
            continue
        yield fieldname.lower()
        yield from tokenize_plain_text(fieldvalue)

def tokenize_upnp_tree(upnp_tree:lxml.etree._Element)->str:
    try:
        upnp_header = upnp_tree.xpath(".//table[@key='response_header']")[0]
    except IndexError:
        raise StopIteration
    yield from parse_response_header(upnp_header)
    upnp_body = upnp_tree.xpath(".//elem[@key='response_body']")[0].text
    if upnp_body is not None:
        parser = etree.XMLParser(encoding='utf8', recover=True, huge_tree=True, ns_clean=True)
        try:
            xml_tree = etree.fromstring(upnp_body.encode('utf8'), parser=parser)
        except Exception as ex:
            pdb.set_trace()
            traceback.print_exc()
        xml_tree = lxml_remove_namespace(xml_tree.getroottree())
        for elem in xml_tree.getiterator():
            if not re.match(r'friendly|manufacturer|model', str(elem.tag), re.I):
                continue
            yield from tokenize_plain_text(elem.text)
    for elem in upnp_tree.xpath(".//elem"):
        if not re.match(r'friendly|manufacturer|model|HostServer', 
                elem.attrib.get('key',''), re.I):
            continue
        yield from tokenize_plain_text(elem.text)

def tokenize_upnp_info(host)->str:
    try:
        upnp_tree = host.xpath(".//script[@id='upnp-info']")[0]
    except IndexError:
        raise StopIteration
    yield from tokenize_upnp_tree(upnp_tree)


def tokenize_broadcast_upnp_info(IDSession:int, ipaddr:str)->str:
    parser = etree.XMLParser(ns_clean=True, encoding='utf-8', huge_tree=True, recover=True)
    tree = etree.parse('nmaplog/%s.xml'%IDSession, parser=parser)
    try:
        upnp_tree  = tree.xpath(".//script[@id='broadcast-upnp-info']/table[@key='%s']"%ipaddr)[0]
    except IndexError:
        raise StopIteration
    yield from tokenize_upnp_tree(upnp_tree)


def tokenize_http_homepage(host:lxml.etree.ElementTree)->str:
    try:
        homepage = host.xpath(".//script[@id='http-homepage']")[0]
    except:
        raise StopIteration
    header = homepage.xpath(".//table[@key='response_header']")[0]
    yield from parse_response_header(header)
    try:
        body = homepage.xpath(".//elem[@key='response_body']")[0].text
    except:
        raise StopIteration
    if body is None:
        raise StopIteration
    htmlcode=html_unescape_backslash_hex(body)
    yield from parse_html(htmlcode)


def get_host_open_ports(xmlfile:str, host_ip:str)->list:
    """
    @return list of open ports ["80t", "1900u"]
    suffix 't' means tcp, 'u' means udp
    """
    ports=[]
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    idx = -1
    for i in range(len(lines)):
        line = lines[i]
        if '<address addr="%s"'%host_ip in line:
            idx=i
            break
    if idx==-1:
        return []
    for idx in range(idx, len(lines)):
        line = lines[idx]
        m= re.search(r'<port protocol="(tcp|udp)" portid="(\d+?)">', line)
        if m:
            protocol = m.group(1)
            portid=int(m.group(2))
            m = re.search(r'<state state="([a-z\|]+?)"', line)
            state = m.group(1)
            if state != 'open':
                continue
            ports += ['%d%s'%(portid,protocol[0])]
            continue
        m= re.search(r'</ports>', line)
        if m:
            break
    return ports

def get_host_osmatch(xmlfile:str, host_ip:str)->list:
    """
    @return list of matched os names
            ["Linux 2.4.18 - 2.4.35 (likely embedded)", 
                "Microsoft Windows Vista SP2, Windows 7 SP1, or Windows Server 2008"]
    """
    """
    <osmatch name="Linux 2.4.18 - 2.4.35 (likely embedded)" accuracy="100" line="37535">
    """
    """
    <osmatch name="Microsoft Windows Vista SP2, Windows 7 SP1, or Windows Server 2008" accuracy="100" line="61921">
    """
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    idx = -1
    for i,line in enumerate(lines):
        if '<address addr="%s"'%host_ip in line:
            idx=i
            break
    if idx==-1:
        return []
    osnames=[]
    for idx, line in enumerate(lines[idx:], start=idx):
        m= re.search(r'<osmatch name="(.+?)" ', line)
        if m:
            osname = m.group(1)
            osnames += [osname]
            continue
        m= re.search(r'</host>', line)
        if m:
            break
    return osnames


def tokenize_text(text:str):
    # any word combined by [a-z0-9_\-.]+ but not started or ended with '.' or '-'
    for tokm in re.finditer(r'(?!\.|\-)[\w\-.]+(?<!\.|-)', text, re.UNICODE|re.DOTALL):
        tok = tokm.group(0).strip('.-').lower()
        if tok:
            yield tok
def tokenize_xml(xmlcode:str)->str:
    for pagm in re.finditer(r'<.+?>|[^<>]+', xmlcode, re.DOTALL|re.UNICODE):
        pag = pagm.group(0)
        if pag[0]=='<':
            tokenize_xml_markup(pag)
        else:
            pag = unescape(pag).strip()
            if is_markup_lang(pag):
                if is_html(pag):
                    tokenize_html(pag)
                else:
                    tokenize_xml(pag)
            else:
                tokenize_text(pag)

def tokenize_hostname(host:lxml.etree.ElementTree)->str:
    try:
        yield host.xpath(".//hostname")[0].attrib['name']
    except IndexError:
        raise StopIteration()


def tokenize_dns(host:lxml.etree.ElementTree)->str:
    try:
        dns=host.xpath(".//script[@id='dns-service-discovery']")[0]
    except IndexError:
        raise StopIteration
    for elem in dns.xpath(".//elem"):
        if not elem.text:
            continue
        yield from tokenize_plain_text(elem.text)


def tokenize_sslcert(host):
    try:
        script=host.xpath(".//script[@id='ssl-cert']")[0]
    except IndexError:
        raise StopIteration
    for elem in script.xpath(".//elem"):
        if not elem.attrib['key'].lower().endswith('name') or not elem.text:
            continue
        yield from tokenize_plain_text(elem.text)


def mac_oui_vendor_lookup(mac_oui)->str:
    import sqlite3
    with sqlite3.connect("ieee_mac_oui.sqlite3") as conn:
        csr = conn.cursor()
        try:
            vendor,*_ = csr.execute("SELECT company_name FROM TMacOui WHERE oui=?", (mac_oui.replace(':','').upper(),)).fetchone()
            return vendor
        except TypeError:
            return None


def tokenize_mac_oui(host):
    try:
        address = host.xpath(".//address[@addrtype='mac']")[0]
    except IndexError:
        raise StopIteration
    oui = address.attrib['addr'][:8]
    yield oui
    try:
        vendor = address.attrib['vendor']
    except KeyError:
        vendor = mac_oui_vendor_lookup(oui)
        if vendor is None:
            raise StopIteration
    yield from tokenize_plain_text(vendor)


def tokenize_osmatch(host):
    """
    <osmatch name="Thomson ST 585 or ST 536i ADSL modem" accuracy="92" line="81215">
    <osmatch name="Nokia IP650 firewall (IPSO 4.0 and CheckPoint Firewall-1/VPN-1 software)" accuracy="90" line="69940">
    <osmatch name="HP LaserJet 4300 printer" accuracy="88" line="27474">
    <osmatch name="Ricoh Aficio 1224C or AP400N printer" accuracy="88" line="74495">
    <osmatch name="AirSpan ProST WiMAX access point" accuracy="85" line="1759">
    """
    for osmatch in host.xpath(".//osmatch"):
        yield from tokenize_plain_text(osmatch.attrib["name"])

def tokenize_openport(host):
    """
    <port protocol="tcp" portid="5000"><state state="open" reason="syn-ack" reason_ttl="64"/><service name="upnp" method="table" conf="3"/></port>

    """
    for openport in host.xpath(".//port/state[@state='open']/.."):
        yield "%s/%s" % (openport.attrib['portid'], openport.attrib['protocol'])


def tokenize_nbstat(host): 
    try:
        nbstat = host.xpath(".//script[@id='nbstat']")[0]
    except:
        raise StopIteration
    for elem in nbstat.xpath(".//elem"):
        if elem.text is None:
            continue
        yield from tokenize_plain_text(elem.text)


def tokenize_nmaplog_host(IDSession:int, ip_addr:str)->str:
    """
     ('upnp', 256878),
     ('http-homepage', 202436),
     ('dns', 100613),
     ('http-headers', 60084),
     ('hostname', 51351),
     ('broadcast-upnp', 23793),
     ('sslcert', 12867),
     ('osmatch', 6023),
     ('openport', 5991),
     ('bjnp-discover', 3416),
     ('nbstat', 3405),
     ('afp-serverinfo', 2348), # Apple Inc. devices
     ('broadcast-dns', 1245),
     ('http-title', 693),
     ('http-qnap-nas-info', 654),
     ('broadcast-bjnp', 480),
     ('wsdd', 477),
     ('broadcast-upnp-unverified', 213),
     ('nbstat-unverified', 18),
     ('afp-serverinfo-unverified', 5),
     ('broadcast-dns-unverified', 3)]
    """
    host = get_host(IDSession, ip_addr)
    if host is None:
        raise StopIteration
    # upweight upnp_info
    yield from nrepeat(3, tokenize_upnp_info(host))
    yield from nrepeat(3, tokenize_broadcast_upnp_info(IDSession, ip_addr))
    yield from tokenize_http_homepage(host)
    yield from tokenize_dns(host)
    yield from tokenize_hostname(host)
    yield from tokenize_sslcert(host)
    yield from nrepeat(3, tokenize_mac_oui(host))
    yield from tokenize_osmatch(host)
    yield from tokenize_openport(host)
    yield from tokenize_nbstat(host)


def main():
    import sys
    idsession = int(sys.argv[1]) if len(sys.argv)>1 else None
    ip_addr = sys.argv[2] if len(sys.argv)>2 else None
    # osnames = get_host_osmatch('nmaplog/344131.xml', '192.168.1.1')
    # toks = [_ for _ in tokenize_nmaplog_host(133, '192.168.1.1')]
    # toks = [_ for _ in tokenize_nmaplog_host(853, '192.168.1.1')]
    if idsession is None:
        idsession, ip_addr = 25, '192.168.11.1'
    toks = [_ for _ in tokenize_nmaplog_host(idsession, ip_addr)]
    import pprint
    pp = pprint.PrettyPrinter()
    pp.pprint(toks)
    # from collections import Counter
    # counter = Counter(toks)
    # # assert "dsldevice.lan" in counter
    # print(counter)

if __name__=='__main__':
    main()

