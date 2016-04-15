# coding: utf-8
from os import path
import os
from web_utils import get_http_resp_content
from urllib import request, parse
import re
from collections import OrderedDict
import sqlite3


def save_txt_file(txt:str, filepath:str):
    from os import path
    folder, fname = path.split(filepath)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(filepath, mode='w', encoding='utf-8') as fout:
        fout.write(txt)

def main():
    conn = sqlite3.connect('ieee_mac_oui.sqlite3')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS TMacOui"
            " (oui TEXT NOT NULL,"
            " company_name TEXT, "
            "PRIMARY KEY (oui) );")
    conn.commit()

    with request.urlopen("http://standards-oui.ieee.org/oui.txt") as fin:
        print(fin.headers.items())
        for line in fin:
            line = line.decode('utf8')
            line = line.strip()
            # E0-43-DB (hex) Shenzhen ViewAt Technology Co.,Ltd.
            m = re.match(r"^[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}", line)
            if not m: 
                while True:
                    try:
                        line = next(fin)
                    except StopIteration:
                        break
                    if not line.strip():
                        break
                continue
            oui = m.group(0).replace('-', '')
            company_name = line.partition("(hex)")[2].strip()
            try:
                next(fin)
            except StopIteration:
                break
            try:
                cursor.execute("INSERT OR REPLACE INTO TMacOui "
                        "(oui, company_name) VALUES"
                        "(:oui, :company_name)", locals())
                print('%(oui)s, %(company_name)s'%locals())
                conn.commit()
            except sqlite3.IntegrityError as ex:
                print(ex.args)

    conn.close()

if __name__ == "__main__":
    main()

