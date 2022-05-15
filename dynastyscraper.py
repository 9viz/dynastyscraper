#!/usr/bin/env python3
#
# This is a really crude script.  This spits out shell-escaped wget
# commands to download the images of the chapters.
#
# Each image is downloaded into "VOLUME_CHAPTER/XXX.png" where VOLUME
# and CHAPTER are the volume and chapter names respectively.  If DRY
# environmental variable is not empty, then this script does not
# create the needed directories beforehand.
#
# Chapter or series URL may be given as arguments to the script.
#
# To read the chapter in zathura(1), use the following command
#
#       zip CHAPTER.zip CHAPTER_IMAGES/*

import json
from os         import mkdir, getenv
from os.path    import splitext, basename
from shlex      import quote as shell_quote
from sys        import argv
import re
import urllib.request as req

import bs4

IMAGE_RE = re.compile(r"//<!\[CDATA\[")
MKDIRP   = not getenv("DRY")

def get_chapter_list(url):
    """Get the list of chapters in URL.

    Returned value is a dictionary { VOLUME: CHAPTERS } where VOLUME
    is the name of the volume and CHAPTERS is a tuple (NAME, URL)
    where NAME is the name of the chapter and URL is the link to the
    chapter.  If the manga is not divided by volumes, then VOLUME is
    an empty string.

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
            chs.append((i.a.string, "https://dynasty-scans.com" + i.a["href"]))

    return ret

def get_images(ch):
    """Get list of image URLs for the chapter with URL CH."""
    soup = bs4.BeautifulSoup(req.urlopen(ch), "html.parser")
    if r := re.search(r"var pages = (\[.*\])", soup.find("script", string=IMAGE_RE).string):
        return [ "https://dynasty-scans.com" + i["image"]
                 for i in json.loads(r.group(1)) ]
    return []

def do1(images, dirname):
    if MKDIRP: mkdir(dirname)
    for n, i in enumerate(images):
        _, ext = splitext(i)
        print(f"wget {i} -O", shell_quote(f"{dirname}/{n+1:03}{ext}"))

def do(url):
    if "chapters" in url:
        do1(get_images(url), basename(url))
    else:
        chp = get_chapter_list(url)
        for vol, ch in chp.items():
            for prefix, url in ch:
                do1(get_images(url), (vol+"_" if vol else "")+prefix)

if __name__ == "__main__":
    for i in argv[1:]:
        do(i)
