#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import re
import traceback
import pdb

def get_host_xml_lines(xmlfile:str, host_ip:str)->list:
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    beg,end,idx = [-1]*3
    for i in range(len(lines)):
        line = lines[i]
        if '<address addr="%s"'%host_ip in line:
            idx=i
            break
    if idx==-1:
        return []
    for beg in range(idx-1, 0, -1):
        line = lines[beg]
        if re.search(r'<host ', line):
            break
    for end in range(idx+1, len(lines), 1):
        line = lines[end]
        if re.search(r'</host>', line):
            break
    return lines[beg:end+1]

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

