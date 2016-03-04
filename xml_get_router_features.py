#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import sys
import traceback
import pdb
import glob
import os
import re
import numpy as np
from nmap_utils import get_host_open_ports


def get_portstates(xmlfile:str)->list:
    portstates=[]
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    idx = -1
    for i in range(len(lines)):
        line = lines[i]
        if re.search(r'<address addr="192\.168\.\d\.(1|254)"', line):
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
            portstates += [('%d%s'%(portid,protocol[0]), state)]
            continue
        m= re.search(r'</ports>', line)
        if m:
            break
    return portstates



g_mac_addr=set()

def get_portstates2(xmlfile:str)->list:
    portstates=[]
    with open(xmlfile, 'r') as fin:
        lines = fin.readlines()
    beg,end,idx = [-1]*3
    for i in range(len(lines)):
        line = lines[i]
        if re.search(r'<address addr="192\.168\.\d\.(1|254)"', line):
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
    for idx in range(beg, end+1):
        line = lines[idx]
        m= re.search(r'<port protocol="(tcp|udp)" portid="(\d+?)">', line)
        if m:
            protocol = m.group(1)
            portid=int(m.group(2))
            m = re.search(r'<state state="([a-z\|]+?)"', line)
            state = m.group(1)
            portstates += [((portid, protocol), state)]
            continue
        m = re.search(r'<address addr="([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})"', line, re.I)
        if m:
            mac_addr = m.group(1).lower()
            global g_mac_addr
            if mac_addr in g_mac_addr:
                return []
            g_mac_addr.add(mac_addr)
            continue
        m= re.search(r'</ports>', line)
        if m:
            break
    return portstates


def main():
    try:
        g_states=('12345udp', 'open','closed','filtered','open|filtered','unknown')
        early_stop = int(sys.argv[1]) if len(sys.argv)>1 else None
        ports = [[0 for _ in range(6)] for _ in range(65535*2)]
        for i in range(65535):
            ports[i][0] = '%dt'%(i+1)
            ports[65535+i][0]='%du'%(i+1)

        xmlfiles = glob.glob1('nmaplog', '*.xml') 
        num_proc=0
        for xmlfile in xmlfiles[:early_stop]:
            portstates = get_portstates2('nmaplog/'+xmlfile)
            for portstate in portstates:
                port, state = portstate
                def port2index(port:(int,str))->int:
                    portid, protocol = port
                    return portid-1 if protocol=='tcp' else 65535+portid-1
                def state2index(state:str)->int:
                    return g_states.index(state)
                ports[port2index(port)][state2index(state)] += 1
            num_proc+=1
        
        # only count open ports
        ports.sort(key=lambda row:sum(row[1:2]), reverse=True)
        def first_zero_port():
            for i in range(65535*2):
                if sum(ports[i][1:2])==0:
                    return i
        fzp = first_zero_port()
        del ports[fzp:]
        print('open_ports=%s'%[_[0] for _ in ports])
        return

        def mode_value(row:tuple)->str:
            maxcol=max(range(1,6), key=lambda k:row[k])
            return g_states[maxcol]
        ports_mode_value = [(port[0],mode_value(port)) for port in ports]
        ports_mode_value.sort(key=lambda kv:(int(kv[0][:-1]),kv[0][-1]))
        print('ports_mode_value=%s'%(ports_mode_value))
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()

if __name__=='__main__':
    main()

