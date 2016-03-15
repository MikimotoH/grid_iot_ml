#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import re
import traceback
import pdb
from nmap_utils import get_host_open_ports, get_host_osmatch
from os import path
import sqlite3
import numpy as np
import ipdb


def get_idx(lines, start, cond):
    for i, line in enumerate(lines[start:], start=start):
        if cond(line):
            return i 
    return -1

def startswith2(l:str, ps:list):
    for p in ps:
        if l.startswith(p):
            return True
    return False

def flatten_listoflist(ll:list)->list:
    from functools import reduce
    return reduce(lambda a,b:a+b, ll, [])

def get_lines_between(xmlfile:str, host_ip:str, begtag, endtag)->list:
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    beg=get_idx(lines,0, lambda l:'<address addr="%s"'%host_ip in l)
    if beg==-1:
        return []
    end=get_idx(lines,beg+1, lambda l:'</host>' in l)
    if end==-1:
        return []
    lines = lines[beg:end]
    beg=get_idx(lines,0, lambda l:begtag in l)
    if beg==-1:
        return []
    end=get_idx(lines,beg+1, lambda l:endtag in l)
    if end==-1:
        return []
    return lines[beg:end]

def wordlist_to_bagofwords(wl:list)->dict:
    bag={}
    for w in wl:
        if w not in bag:
            bag[w]=1
        else:
            bag[w]+=1
    return bag

def remove_uuid(s:str)->str:
    s = re.sub('[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', ' ', s, flags=re.I)
    s = re.sub('[a-f0-9]{24,}', ' ', s, flags=re.I)
    return s

def remove_html_tags(s:str)->str:
    if False:
        #if '<script ' in s:
        #    ipdb.set_trace()
        s = re.sub(r'<script.+?>.*?</script>', ' script ', s)
        s = re.sub(r'<.+?>', ' ', s)
        return s
    else:
        import html2text
        h2t = html2text.HTML2Text()
        h2t.body_width=0
        h2t.ignore_images=True
        h2t.ignore_links=True
        h2t.ignore_emphasis=True
        s = h2t.handle(s)
        return s.replace('--|','')

def strip_punc(s:str)->str:
    return s.strip("""|-,.:;'" \n\t#`()""")

def get_http_homepage(xmlfile:str, host_ip:str) -> dict:
    lines = get_lines_between(xmlfile,host_ip,
            '<script id="http-homepage"','</script>')
    if not lines:
        return {}
    lines = [re.sub(r'<.+?>','', _) for _ in lines]

    lines = ''.join(_ for _ in lines)
    header, body, *_ = lines.split('\n\n')
    
    header = [_.split(':',1) for _ in header.splitlines() if ':' in _]
    header = flatten_listoflist([k.strip(),v.strip()] for k,v in header if k not in 
            ['Date','Expires','Pragma','Connection','Content-Type','ETag', 
                'Last-Modified', 'Accept-Ranges','Content-Length', 'Cache-Control'])
    from html import unescape
    header = [unescape(_) for _ in header]
    header = [remove_uuid(_) for _ in header]
    header = flatten_listoflist(re.split(r""",|\ |=|"|'|;|:|\(|\)""", _) for _ in header)

    body = unescape(body)
    body = unescape(body)

    body = re.sub(r'\\x([0-9A-Fa-f]{2})', lambda m:chr(int(m.group(1),16)), body)
    body = remove_uuid(body)
    body = remove_html_tags(body)
    body = [_ for _ in re.split(r"""=|"|\ |\t|\n|\r|,|;""", body) if _]
    body = [_ for _ in (strip_punc(_) for _ in body) if _]
    body = [_ for _ in (strip_punc(_) for _ in body) if _]

    return wordlist_to_bagofwords(_.strip() for _ in header+body if _.strip())

def xml_to_bag(xml:str)->list:
    return [_ for _ in [_.strip(' \t\n=') for _ in 
        re.split(r"""</|<\?|\?>|<|>|"|\ |\t|\n|\r|\(|\)""", xml)] if _]


def get_upnp_info(xmlfile:str, host_ip:str)->dict:
    lines = get_lines_between(xmlfile, host_ip, 
            '<script id="upnp-info"', '</script>')
    if not lines:
        return {}
    from html import unescape
    elms=[]
    for l in lines:
        m = re.search(r'<elem key="(.+?)"', l)
        if m:
            if m.group(1)=='response_body':
                elms += xml_to_bag(unescape(re.sub(r'<.+?>', '', l)))
            else:
                elms += re.sub(r'<.+?>', '', l).strip().split()
                elms += m.group(1)
    elms = [unescape(_) for _ in elms]
    elms = [re.sub(r'\\x([0-9A-Fa-f]{2})', lambda m:chr(int(m.group(1),16)), _) for _ in elms]
    elms = [remove_uuid(_) for _ in elms]

    elms = [_ for _ in (strip_punc(_) for _ in elms) if _]
    elms = [_ for _ in (strip_punc(_) for _ in elms) if _]
    elms = flatten_listoflist(_.split() for _ in elms)
    return wordlist_to_bagofwords(elms)


def bag_update(bag:dict, bag1:dict)->dict:
    for w in bag1:
        if w not in bag:
            bag[w] = bag1[w]
        else:
            bag[w]+= bag1[w]
    return bag
    
def main():
    import sqlite3
    conn = sqlite3.connect('unknown_routers.sqlite3')
    csr = conn.cursor()
    rows = csr.execute("SELECT IDSession, ip_addr FROM Routers WHERE LOWER(brand) LIKE 'asus%'").fetchall()
    bag={}
    for IDSession, host_ip in rows:
        bag_update(bag, get_http_homepage('nmaplog/%s.xml'%IDSession, host_ip))
        bag_update(bag, get_upnp_info('nmaplog/%s.xml'%IDSession, host_ip))
    import json
    with open('asus_http_upnp_bagofwords.json', 'w') as fout:
        from collections import OrderedDict
        json.dump( OrderedDict(sorted(bag.items(), key=lambda kv:kv[1], reverse=True)), fout, indent=2)


if __name__=='__main__':
    main()

