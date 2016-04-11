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
from parse_html import parse_html

def get_host_xml_lines(xmlfile:str, host_ip:str)->list:
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    def find_pivot():
        for i in range(len(lines)):
            line = lines[i]
            if '<address addr="%s"'%host_ip in line:
                return i
    pivot = find_pivot()
    if pivot is None:
        return []
    def find_beg():
        for i in range(pivot-1, -1, -1):
            line = lines[i]
            if line.startswith(r'<host '):
                return i
    beg = find_beg()
    if beg is None:
        beg=0
    def find_end():
        for i in range(pivot+1, len(lines), 1):
            line = lines[i]
            if line.startswith(r'</host>'):
                return i
    end = find_end()
    if end is None:
        end=len(lines)-1
    return lines[beg:end+1]

def is_html(ss):
    return ss.strip().startswith('<')

def tokenize_nmaplog_host(IDSession:int, ip_addr:str)->str:
    xml_lines = get_host_xml_lines("nmaplog/%s.xml"%IDSession, ip_addr)
    for line in xml_lines:
        for parag in re.finditer(r'<.+?>|[^<>]+', line, re.DOTALL):
            if parag.startswith('<'):
                yield from parse_xml_markup(parag)
            else:
                yield from parse_xml_text(unescape(parag))

                words = parag.strip('<>').split()
                for word in words:
                    if word.startswith('"'):
                        word = unescape(word.strip('"'))
                        if is_html(word):
                            yield from parse_html(word)
                        else:
                            yield from word.split()

"""
In [24]: counter.most_common(26)
Out[24]:
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
 ('afp-serverinfo', 2348),
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

def lxml_remove_namespace(xml_tree:lxml.etree.ElementTree):
    root = xml_tree.getroot()
    for elem in root.getiterator():
        if not hasattr(elem.tag, 'find'): continue
        i = elem.tag.find('}')
        if i >= 0:
            elem.tag = elem.tag[i+1:]
    objectify.deannotate(root, cleanup_namespaces=True)
    return root

def parse_response_header(header)->str:
    for child in upnp_header.getchildren():
        if not child.text:
            continue
        text = child.text
        fieldname, fieldvalue = text.split(': ', maxsplit=1)
        if fieldname.lower() in ['content-length', 'date', 'last-modified', 'connection', 'content-type']:
            continue
        yield fieldname
        for tok in re.split(r' ', fieldvalue):
            yield tok

def get_upnp_info(host)->str:
    try:
        upnp_info = host.xpath(".//script[@id='upnp-info']")[0]
    except IndexError:
        return
    upnp_header = upnp_info.xpath(".//table[@key='response_header']")[0]
    yield from parse_response_header(upnp_header)
    upnp_status = upnp_info.xpath(".//elem[@key='response_status']")[0].text
    yield upnp_status
    upnp_body = upnp_info.xpath(".//elem[@key='response_body']")[0].text
    xml_tree = etree.fromstring(upnp_body)
    root = lxml_remove_namespace(xml_tree.getroottree())
    for elem in xml_tree.getiterator():
        text = elem.text.strip()
        if not elem.text.strip():
            continue
        for tok in re.split(r' ', text):
            yield tok

def get_host(IDSession:int, ip_addr:str)->ElementTree:
    parser = etree.XMLParser(encoding='utf-8', huge_tree=True, recover=True)
    xml_lines = get_host_xml_lines('nmaplog/%s.xml'%IDSession, ip_addr)
    return etree.fromstring(''.join(xml_lines), parser=parser)


def html_to_bagofwords_1(htmlcode:str):
    htmlcode = unescape_backslash_hex(htmlcode)
    soup = BeautifulSoup(htmlcode, 'lxml')
    for s in soup(["script", "style"]):
        s.extract()
    for parag in soup.getTextRecursively():
        for sentence in re.split(r' ', parag):

    txt = [_.strip(' \r\n\t.,;:-|') for _ in txt.split()]
    txt = [_ for _ in txt if _]
    return txt

def get_homepage(host:lxml.etree.ElementTree)->str:
    homepage = host.xpath(".//script[@id='http-homepage']")[0]
    header = homepage.xpath(".//table[@key='reponse_header']")[0]
    yield from parse_response_header(header)
    body = homepage.xpath(".//table[@key='reponse_body']")[0]
    htmltext = body.text

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


def main():
    osnames = get_host_osmatch('nmaplog/344131.xml', '192.168.1.1')
if __name__=='__main__':
    main()

