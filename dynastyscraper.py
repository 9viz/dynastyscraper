#!/usr/bin/env python3
import bs4
from shlex import quote as shell_quote
import urllib.request as req

from sys import argv

base = argv[1]

soup = bs4.BeautifulSoup(req.urlopen(base), "html.parser")

# Chapters.  May or may not be divided by volumes.
chapters = soup.find("dl", class_="chapter-list")

# Volume?
volp = bool(chapters.find("dt"))

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
    ret = {}

    for ch in dds:
        print("wget {} -O {}.cbz".format(
            shell_quote("https://dynasty-scans.com" + ch.a["href"] + "/download"),
            shell_quote(dt + ch.a.string)
        ))

    return

if volp:
    vol = ""
    dds = []
    for i in chapters:
        if not isinstance(i, bs4.element.Tag):
            continue

        if i.name == "dt":
            print_links(dds, vol + "_")
            vol = i.string
            dds = []
            continue
        elif i.name == "dd":
            dds.append(i)
    if dds: print_links(dds, (vol + "_") if vol else "")
else:
    print_links(chapters.find_all("dd"))
