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
from os.path    import exists as file_exists_p
from shlex      import quote as shell_quote
from sys        import argv
import re
import urllib.request as req

import bs4

DYNASTY_IMAGE_RE = re.compile(r"//<!\[CDATA\[")
BATOTO_IMAGE_RE  = re.compile(r"(?:const|var) images = \[")
JS_CTXT          = None
UA               = { "User-Agent": "Chrome/96.0.4664.110" }
MKDIRP           = not getenv("DRY")

def dynasty_get_chapter_list(url):
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
    if chs:
        ret[vol] = chs
    return ret

def dynasty_get_images(ch):
    """Get list of image URLs for the chapter with URL CH."""
    soup = bs4.BeautifulSoup(req.urlopen(ch), "html.parser")
    if r := re.search(r"var pages = (\[.*\])", soup.find("script", string=DYNASTY_IMAGE_RE).string):
        return [ "https://dynasty-scans.com" + i["image"]
                 for i in json.loads(r.group(1)) ]
    return []

def batoto_get_chapter_list(url):
    """Get the list of chapters in URL.

    Returned value is a list of (NAME, URL) where NAME is the name of
    chapter and URL is the link to the chapter.

    """
    chs = []
    # User-Agent is need to be set otherwise cloudfare pops up.
    soup = bs4.BeautifulSoup(req.urlopen(req.Request(url, headers=UA)),
                             "html.parser")
    for i in soup.find_all("a", class_="visited chapt"):
        # The name of the chapter is surrounded by newlines for some
        # reason.
        chs.append((i.text.strip(), "https://bato.to" + i["href"]))

    chs.reverse()
    return chs

def batoto_get_images(ch):
    """Get list of image URLs for the chapter CH.

    I came to know of duktape thanks to the Tachiyomi bato.to
    extension.

    """
    def js_eval(string):
        """Evalulate JavaScript code in the string STRING."""
        import pyduktape
        global JS_CTXT
        if not JS_CTXT:
            JS_CTXT = pyduktape.DuktapeContext()
            if not file_exists_p("./crypto.js"):
                cryptojs = req.urlopen(req.Request(
                    # The same URL tachiyomi uses.
                    "https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.0.0/crypto-js.min.js",
                    headers=UA))
                with open("./crypto.js", "w") as f:
                    f.write(cryptojs.read().decode("utf-8"))
            JS_CTXT.eval_js_file("./crypto.js")
        return JS_CTXT.eval_js(string)

    soup = bs4.BeautifulSoup(req.urlopen(req.Request(ch, headers=UA)), "html.parser")
    js = soup.find("script", text=BATOTO_IMAGE_RE).string

    # Most of this magic can be figured out by reading the JavaScript
    # sources in a chapter page.  Alternatively, refer to
    # https://github.com/tachiyomiorg/tachiyomi-extensions/blob/master/src/all/batoto/src/eu/kanade/tachiyomi/extension/all/batoto/BatoTo.kt
    server = re.search(r"(?:const|var) server = ([^;]+);", js).group(1)
    batojs = re.search(r"(?:const|var) batojs = ([^;]+);", js).group(1)
    base = js_eval(f"CryptoJS.AES.decrypt({server} ,{batojs}).toString(CryptoJS.enc.Utf8);").strip("\"")
    return [ base + i for i in json.loads(re.search(r"(?:const|var) images = (\[.*\]);", js).group(1)) ]

def do1(images, dirname):
    if MKDIRP: mkdir(dirname)
    for n, i in enumerate(images):
        _, ext = splitext(i)
        if "?" in ext:
            ext, _, _ = ext.partition("?")
        print("wget {} -O {}".format(shell_quote(i), shell_quote(f"{dirname}/{n+1:03}{ext}")))

def do(url):
    if "dynasty-scans.com" in url:
        if "chapters" in url:
            do1(dynasty_get_images(url), basename(url))
        else:
            chp = dynasty_get_chapter_list(url)
            for vol, ch in chp.items():
                for prefix, url in ch:
                    do1(dynasty_get_images(url), (vol+"_" if vol else "")+prefix)
    elif "bato.to" in url:
        if "chapter" in url:
            do1(batoto_get_images(url), basename(url))
        else:
            chp = batoto_get_chapter_list(url)
            for name, ch in chp:
                do1(batoto_get_images(ch), name.replace("\n", "", True))

if __name__ == "__main__":
    for i in argv[1:]:
        do(i)
