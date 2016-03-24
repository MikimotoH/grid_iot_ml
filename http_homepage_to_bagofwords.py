#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from lxml import etree
import lxml
import re
from functools import reduce
from itertools import takewhile
from bs4 import BeautifulSoup

def html_to_bagofwords_0(htmlcode:str, include_tags=True):
    txt = re.split(r"\W+", htmlcode)
    txt = [_ for _ in txt if _.lower() not in 
            ['html','head','title','body', 'h1','h2','div','span','script','style', 
                'input', 'table', 'tbody', 'tr', 'td', 'tbody', 'type', 'class', 
                'value', 'select', 'option', 'var']]
    txt = [_ for _ in txt if _]
    return txt
def html_to_bagofwords_1(htmlcode:str, include_tags=True):
    soup = BeautifulSoup(htmlcode, 'lxml')
    for s in soup(["script", "style"]):
        s.extract()
    txt = soup.get_text()
    txt = [_.strip(' \r\n\t.,;:') for _ in txt.split()]
    txt = [_ for _ in txt if _]
    return txt

def html_to_bagofwords(htmlcode:str, include_tags=True)->list:
    for scriptmatch in re.finditer(r'<script.*>(.+)</script>', htmlcode):
        javascript = scriptmatch.group(1)
        comments = re.findall(r'/\*.(*?)\*/', javascript)
        comments += re.findall(r'//.*$', javascript)
        # remove comments
        javascript = re.sub(r'/\*.*?\*/', ' ', javascript)
        javascript = javascript = re.sub(r'//.*$', '', javascript)
        # remove strings
        strings = re.findall(r'"(.*(?!\"))"', javascript)
        strings += re.findall(r"'(.*?(?!\'))'", javascript)
        codes = re.split(r'\W+', javascript)
        
    
    txt = BeautifulSoup(htmlcode, 'lxml').get_text()
    txt = [_.strip(' \r\n\t;:.,\'"?#(){}+=-/*|![]<>&') for _ in txt.split()]
    txt = [_ for _ in txt if _]
    if not include_tags:
        return txt
    tags = [re.split(r"""<--|-->|<\!|</|/>|<\?|\?>|<|>|\ |;|"|=""",_) for _ in re.findall(r'<.+?>', htmlcode)]
    tags = [_.strip(' \n\r\t#/-') for _ in reduce(lambda a,b:a+b, tags,[])]
    tags = [_ for _ in tags if _]
    return txt+tags

def http_headers_to_bagofwords(hdrs:list)->list:
    hdrs = [_.split(':',1) for _ in hdrs]
    hdrs = [(k,v) for k,v in hdrs if k.lower() not in ['content-length', 
        'last-modified', 'date', 'expires', 'cache-control', 'content-type', 
        'pragma', 'connection']]
    hdrs = [[k]+re.split(r';|,|\ ', v) for k,v in hdrs]
    hdrs = list(reduce(lambda a,b:a+b, hdrs, []))
    hdrs = [_.strip(' \r\n;,') for _ in hdrs]
    hdrs = [_ for _ in hdrs if _]
    return hdrs;

def get_host(id_session:int, host_ip:str)->lxml.etree._Element:
    parser = etree.XMLParser(encoding='utf-8', huge_tree=True,recover=True)
    tree = etree.parse('nmaplog/%s.xml'%id_session, parser=parser)
    hosts = tree.xpath(".//address[@addr='%s']/.."%host_ip)
    return hosts[0] if hosts else None

def get_homepage_as_bagofwords(id_session:int, host_ip:str, **kwargs)->list:
    """
    optional include_tags=True : include HTML tags
    optional include_hostname=True : include hostname
    optional get_upnp_info=True : get script id='upnp-info'
    """
    include_tags = kwargs.get('include_tags', True)
    include_hostname = kwargs.get('include_hostname', True)
    get_upnp_info = kwargs.get('get_upnp_info', True)
    host = get_host(id_session, host_ip) 
    if host is None:
        return []
    
    hostname = []
    if include_hostname:
        try:
            hostname = [host.xpath('.//hostname')[0].attrib['name']]
        except (AttributeError,IndexError):
            pass

    homepage_bow=[]
    try:
        script = host.xpath(".//script[@id='http-homepage']")[0]
        hdrs = [_.text for _ in script.xpath(".//table[@key='response_header']/elem") if _.text]
        htmlcode = script.xpath(".//elem[@key='response_body']")[0].text
        homepage_bow = http_headers_to_bagofwords(hdrs)
        if htmlcode is not None:
            homepage_bow += html_to_bagofwords_1(htmlcode, include_tags)
    except (AttributeError,IndexError):
        pass

    upnp = []
    if get_upnp_info:
        try:
            script = host.xpath(".//script[@id='upnp-info']")[0]
            for key in ['friendlyName', 'manufacturer', 'modelDescription', 'modelName', \
                    'modelNumber', 'HostServer']:
                upnp += script.xpath(".//elem[@key='%s']"%key)[0].text.split()
        except IndexError:
            pass
    return  homepage_bow + hostname + upnp


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
    txt = html_to_bagofwords(htmlcode)
    return hdrs+txt


