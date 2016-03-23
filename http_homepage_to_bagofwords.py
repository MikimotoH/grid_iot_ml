#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from lxml import etree
import lxml
import re
from functools import reduce
from itertools import takewhile

def html_to_text(htmlcode:str, include_tags=True)->list:
    from bs4 import BeautifulSoup
    txt = BeautifulSoup(htmlcode, 'lxml').get_text()
    txt = [_.strip(' \r\n\t;.,\'"?#()') for _ in txt.split()]
    if not include_tags:
        return txt
    tags = [re.split(r"""<--|-->|<\!|</|/>|<\?|\?>|<|>|\ |;|"|=""",_) for _ in re.findall(r'<.+?>', htmlcode)]
    tags = [_.strip() for _ in reduce(lambda a,b:a+b, tags) if _.strip()]
    return txt+tags

def http_headers_to_bagofwords(hdrs:list)->list:
    hdrs = [_.split(':',1) for _ in hdrs]
    hdrs = [(k,v) for k,v in hdrs if k.lower() not in ['content-length','last-modified', 'date', 'expires']]
    hdrs = [[k]+re.split(r';|,|\ ', v) for k,v in hdrs]
    hdrs = list(reduce(lambda a,b:a+b, hdrs))
    hdrs = [_.strip(' \r\n;,') for _ in hdrs]
    hdrs = [_ for _ in hdrs if _]
    return hdrs;

def get_host(id_session:int, host_ip:str)->lxml.etree._Element:
    parser = etree.XMLParser(encoding='utf-8', huge_tree=True,recover=True)
    tree = etree.parse('nmaplog/%s.xml'%id_session, parser=parser)
    hosts = tree.xpath(".//address[@addr='%s']/.."%host_ip)
    return hosts[0] if hosts else None

def get_homepage_as_bagofwords(id_session:int, host_ip:str)->list:
    host = get_host(id_session, host_ip) 
    if host is None:
        return []
    elems = [_.text for _ in host.xpath(".//script[@id='http-homepage']//elem")]
    if not len(elems):
        return []
    txt = html_to_text(elems[-1], True)
    hdrs = http_headers_to_bagofwords(list(takewhile(lambda x:x, elems)))
    return hdrs + txt


def get_tm_vul_dns_hijack(id_session, host_ip):
    host = get_host(id_session, host_ip) 
    if host is None:
        return []
    try:
        scrout = host.xpath(".//script[@id='%s']"%('tm-vul-dns-hijack'))[0]
    except IndexError:
        return []
    hdrs = [_.text for _ in scrout.xpath(".//table[@key='rawheader']/elem")]
    hdrs = http_headers_to_bagofwords(list(takewhile(lambda x:x, hdrs)))

    htmlcode = scrout.xpath(".//elem[@key='body']")[0].text
    txt = html_to_text(htmlcode)
    return hdrs+txt


