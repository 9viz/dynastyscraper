#!/usr/bin/env python3
#
# This is a really crude script.
# Dynasty url is the first argument.  Spats out shell-escaped wget
# commands to get the cbzs.  Tested with the following:
# 1. https://dynasty-scans.com/series/riko_haru_irukawa_hot_springs
# 2. https://dynasty-scans.com/series/sakura_trick
# 3. https://dynasty-scans.com/series/4_koma_starlight

import json
from os         import mkdir
from os.path    import splitext, basename
from shlex      import quote as shell_quote
from sys        import argv
import re
import urllib.request as req

import bs4

IMAGE_RE = re.compile(r"//<!\[CDATA\[")

def get_chapter_list(url):
    """Get the list of chapters in URL.

    Returned value is a dictionary { VOLUME: CHAPTERS } where VOLUME
    is the name of the volume and CHAPTERS is a list of URLs to the
    chapters URLs.  If the manga is not divided by volumes, then
    VOLUME is an empty string.

    """
    soup = bs4.BeautifulSoup(req.urlopen(url), "html.parser")
    ret = {}
    vol = ""
    chs = []
    chp = soup.find("dl", class_="chapter-list")

    for i in chp:
        if not isinstance(i, bs4.element.Tag):
            continue
        if i.name == "dt":
            if chs: ret[vol] = chs
            vol = i.string
            chs = []
        elif i.name == "dd":
            chs.append("https://dynasty-scans.com" + i.a["href"])

    return ret

def get_images(ch):
    """Get list of image URLs for the chapter with URL CH."""
    soup = bs4.BeautifulSoup(req.urlopen(ch), "html.parser")
    if r := re.search(r"var pages = (\[.*\])", soup.find("script", string=IMAGE_RE).string):
        return [ "https://dynasty-scans.com" + i["image"]
                 for i in json.loads(r.group(1)) ]
    return []

def do1(images, dirname):
    d = shell_quote(dirname)
    # mkdir(dirname)
    for n, i in enumerate(images):
        _, ext = splitext(i)
        print(f"wget {i} -O {d}/{n+1:03}{ext}")

def do(url):
    if "chapters" in url:
        do1(get_images(url), basename(url))
    else:
        chp = get_chapter_list(url)
        for vol, ch in chp.items():
            for i in ch:
                do1(get_images(i), vol+"_"+basename(i))

if __name__ == "__main__":
    for i in argv[1:]:
        do(i)
