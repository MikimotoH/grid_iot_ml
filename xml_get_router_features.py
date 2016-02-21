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
from lxml.etree import XMLParser, parse
import io

"""
host = nmaprun/host/address[@addr=~"\d{1,3}\.\d{1,3}\.\d{1,3}\.1"]
host/ports/port[@protocol="tcp"|"udp"][@portid="22"(1-49152)]/state[@state="open"|"closed"|"filtered"|"unfiltered"|"open|filtered"|"close|filtered"|"unknown"]

80_tcp_o = 1
22_tcp_o = 1
23_tcp_o = 1
23_tcp_uk = 1
23_tcp_c  = 1
1900_udp_o = 1
"""

# csv_file = 'select_nmaplog_from_DRSourcingRawLog_dbo_nmaplog_WHERE_IDSession_201602080751.csv'
# csv.field_size_limit(sys.maxsize-1)

def get_portstates(root):
    hosts = root.xpath(r".//address[re:match(@addr, '192\.168\.\d+\.1\b')]/..", namespaces={"re": "http://exslt.org/regular-expressions"})
    if not hosts:
        hosts = root.xpath(r".//address[re:match(@addr, '192\.168\.\d+\.254\b')]/..", namespaces={"re": "http://exslt.org/regular-expressions"})
        if not hosts:
            return []
    host=hosts[0]
    portstates = ['_'.join([_.attrib['portid'],_.attrib['protocol'],_.xpath('.//state')[0].attrib['state']]) for _ in host.xpath('.//port')]
    return list(set(portstates))

histogram={}
def main():
    os.chdir('nmaplog')
    global histogram
    xmlfiles = glob.glob('*.xml') 
    numXmlFiles = len(xmlfiles)
    idSessions  = sorted(int(re.match(r'(\d+)\.xml', _).group(1)) for _ in xmlfiles)
    huge_xml_parser = XMLParser(encoding='utf-8', recover=True, huge_tree=True)
    
    try:
        for idsession in idSessions:
            if not path.exists('%d.xml'%idsession):
                continue
            try:
                root = etree.parse('%d.xml'%idsession, parser=huge_xml_parser)
            except etree.XMLSyntaxError as ex:
                with open('%d.xml'%idsession, 'r') as fin:
                    xmlsrc = fin.read()
                xmlsrc += "</nmaprun>"
                with io.BytesIO(xmlsrc.encode('utf-8')) as xmlstream:
                    try:
                        root = etree.parse(xmlstream, parser=huge_xml_parser)
                    except etree.XMLSyntaxError as ex:
                        print('%d.xml parse error'%idsession)
                        print(ex)
                        continue
                
            portstates = get_portstates(root)
            for portstate in portstates:
                if portstate in histogram.keys():
                    histogram[portstate].append(idsession)
                else:
                    histogram[portstate] = [idsession]
        important_ports = sorted(histogram.keys(), key=lambda k:len(histogram[k]), reverse=True)
        print(important_ports)
    except Exception as ex:
        pdb.set_trace()
        traceback.print_exc()

if __name__=='__main__':
    main()
