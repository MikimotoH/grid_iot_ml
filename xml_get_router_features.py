#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import xml.dom.minidom
from lxml import etree
import sys
import re
from os import path
import traceback
import pdb
import glob
import os
import re
import numpy as np
import gc

"""
host = nmaprun/host/address[@addr=~"\d{1,3}\.\d{1,3}\.\d{1,3}\.1"]
host/ports/port[@protocol="tcp"|"udp"][@portid="22"(1-49152)]/state[@state="open"|"closed"|"filtered"|"unfiltered"|"open|filtered"|"close|filtered"|"unknown"]

80_tcp = 1.0 opened
22_tcp = 1.0 opened
23_tcp = 0.0 closed
23_tcp = float('NaN')
23_tcp_c  = 1
1900_udp_o = 1
"""

# csv_file = 'select_nmaplog_from_DRSourcingRawLog_dbo_nmaplog_WHERE_IDSession_201602080751.csv'
# csv.field_size_limit(sys.maxsize-1)

g_mac_addr=set()
def get_portstates(xmlfile):
    try:
        huge_xml_parser = etree.XMLParser(encoding='utf-8', recover=True, huge_tree=True)
        try:
            root = etree.parse(xmlfile, parser=huge_xml_parser)
        except etree.XMLSyntaxError as ex:
            print('%s error'%xmlfile); print(ex)
            return []
        # psv={'open':100, 'closed':0, 'filtered':50, 'open|filtered':75, 'unknown':float('NaN')}
        # hosts = root.xpath(r".//address[re:match(@addr, '192\.168\.\d+\.(1\b|254\b)')]/..", namespaces={"re": "http://exslt.org/regular-expressions"})
        hosts = [_.getparent() for _ in root.findall('.//address') if re.match(r'192\.168\.\d\.(1\b|254\b)', _.attrib['addr']) ]
        if not hosts:
            return []
        host=hosts[0]
        mac_addr = next((_ for _ in host.findall('address') if re.match(r'[0-9a-f]{2}:',_.attrib['addr'],re.I)), None)
        if mac_addr is not None:
            global g_mac_addr
            if mac_addr in g_mac_addr:
                return []
            g_mac_addr.add(mac_addr)
        
        portstates = []
        for port in host.findall('.//port'):
            portid = port.attrib['portid']
            protocol = port.attrib['protocol']
            states = port.findall('state')
            state = states[0].attrib['state']
            portstates += [((int(portid),protocol), state)]
        # portstates = [[_.attrib['portid']+'_'+_.attrib['protocol'], psv[_.xpath('.//state')[0].attrib['state']]) for _ in host.xpath('.//port')]
        return portstates
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()

def get_portstates2(xmlfile:str)->list:
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


def get_mode_value(ll:list)->str:
    states = set(ll)
    statescount = {s:ll.count(s) for s in states}
    return max(states, key=lambda s:statescount[s])
def get_mode_value2(statescount:dict)->str:
    return max(statescount.keys(), key=lambda s:statescount[s])

def port2index(port:(int,str))->int:
    portid, protocol = port
    return portid-1 if protocol=='tcp' else 65535+portid-1
g_states=('12345udp', 'open','closed','filtered','open|filtered','unknown')
def state2index(state:str)->int:
    global g_states
    return g_states.index(state)

def main():
    try:
        early_drop = int(sys.argv[1]) if len(sys.argv)>1 else None
        ports = [[0 for _ in range(6)] for _ in range(65535*2)]
        for i in range(65535):
            ports[i][0] = '%dt'%(i+1)
            ports[65535+i][0]='%du'%(i+1)

        xmlfiles = glob.glob1('nmaplog', '*.xml') 
        num_proc=0
        for xmlfile in xmlfiles[:early_drop]:
            portstates = get_portstates2('nmaplog/'+xmlfile)
            for portstate in portstates:
                port, state = portstate
                ports[port2index(port)][state2index(state)] += 1
            num_proc+=1
        
        ports.sort(key=lambda row:sum(row[1:]), reverse=True)
        def first_zero_port():
            for i in range(65535*2):
                if sum(ports[i][1:])==0:
                    return i
        fzp = first_zero_port()
        del ports[fzp:]
        print('important_ports=%s'%[_[0] for _ in ports])

        def mode_value(row:tuple)->str:
            maxcol=max(range(1,6), key=lambda k:row[k])
            global g_states
            return g_states[maxcol]
        ports_mode_value = [(port[0],mode_value(port)) for port in ports]
        ports_mode_value.sort(key=lambda kv:(int(kv[0][:-1]),kv[0][-1]))
        print('ports_mode_value=%s'%(ports_mode_value))
        global g_mac_addr
        print('g_mac_addr=%s'%g_mac_addr)
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()

if __name__=='__main__':
    main()
