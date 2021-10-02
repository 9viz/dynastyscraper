#!/usr/bin/env python3
#
# This is a really crude script.
# Dynasty url is the first argument.  Spats out shell-escaped wget
# commands to get the cbzs.  Tested with the following:
# 1. https://dynasty-scans.com/series/riko_haru_irukawa_hot_springs
# 2. https://dynasty-scans.com/series/sakura_trick
# 3. https://dynasty-scans.com/series/4_koma_starlight

import bs4
from shlex import quote as shell_quote
import urllib.request as req

from sys import argv

base = argv[1]

soup = bs4.BeautifulSoup(req.urlopen(base), "html.parser")

# Chapters.  May or may not be divided by volumes.
chapters = soup.find("dl", class_="chapter-list")

# dt is usually the volume number.
# Return a dictionary with url as key, filename as val
# def get_links(dds, dt=""):
#     ret = {}
#
#     for ch in dds:
#         ret["https://dynasty-scans.com" + ch.a["href"] + "/download"] = dt + ch.a.string
#
#     return ret

def print_links(dds, dt=""):
    for ch in dds:
        print("wget {} -O {}.cbz".format(
            shell_quote("https://dynasty-scans.com" + ch.a["href"] + "/download"),
            shell_quote(dt + ch.a.string)
        ))

vol = ""
dds = []
for i in chapters:
    if not isinstance(i, bs4.element.Tag):
        continue

    if i.name == "dt":
        print_links(dds, vol + "_")
        vol = i.string
        dds = []
    elif i.name == "dd":
        dds.append(i)
if dds: print_links(dds, (vol + "_") if vol else "")
