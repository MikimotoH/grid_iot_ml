#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import re
import traceback
import pdb
from nmap_utils import get_host_open_ports, get_host_osmatch
from os import path
import sqlite3
import numpy as np


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

def get_http_homepage(xmlfile:str, host_ip:str) -> set:
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    idx=get_idx(lines,0, lambda l:'<address addr="%s"'%host_ip in l)
    if idx==-1:
        return []
    beg=get_idx(lines,idx, lambda l:'<script id="http-homepage"' in l)
    if beg==-1:
        return []
    end=get_idx(lines,beg, lambda l:'</script>' in l)
    if end==-1:
        return []
    lines = [re.sub(r'<.+?>','', _) for _ in lines[beg:end]]
    lines = ''.join(_ for _ in lines)

    header, body = lines.split('\n\n')
    header= header.splitlines()
    header = [_.split(':')[1].strip() for _ in header if ':' in _ and not 
            startswith2(_, ['Date:', 'Expires:','Pragma:', 'Connection:', 'Content-Type:'])]
    from html import unescape
    from functools import reduce
    header = [unescape(_) for _ in header]
    header = reduce(lambda a,b:a+b, [re.split(r""",|\ |=|"|'|;|:""", _) for _ in header])
    header = [_.strip() for _ in header if _.strip()]

    body = unescape(body)
    body = re.sub('<.+?>', ' ', body)
    body = unescape(body)
    body = [_ for _ in re.split(r"""</|>|'|"|\ |:|;|,|\.|\t|\n""", body) if _]
    body = [_.strip() for _ in body if _.strip()]

    bags={}
    for w in header+body:
        if w not in bags:
            bags[w]=1
        else:
            bags[w]+=1
    return bags

    
def main():
    osnames = get_http_homepage('nmaplog/1361.xml', '192.168.0.1')
if __name__=='__main__':
    main()

