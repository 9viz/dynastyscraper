#!/usr/bin/env python3
#
# Licensed under BSD 2-Clause License.
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
import multiprocessing as multiproc
from os         import mkdir, getenv
from os.path    import splitext, basename
from os.path    import exists as file_exists_p
from shlex      import quote as shell_quote
from sys        import argv
from urllib.parse import urlparse
import re
import urllib.request as req

import bs4

DYNASTY_IMAGE_RE = re.compile(r"//<!\[CDATA\[")
BATOTO_IMAGE_RE_1  = re.compile(r"(?:const|var) images = \[")
BATOTO_IMAGE_RE_2  = re.compile(r"(?:const|var) imgHttpLis = \[")
REDDIT_RE = re.compile(r"https?://(?:www\.|m\.|np\.)?reddit\.com/")
IMGUR_RE = re.compile(r"https?://(?:www\.|m\.|i\.)?imgur\.com/")
CUBARI_IMGUR_RE = re.compile(r"https?://cubari\.moe/read/imgur/([0-9A-Za-z]+)/?")
DANKEMOE_BASE_API_PATH = "https://danke.moe/api/series/"
DANKEMOE_MEDIAURL = "https://danke.moe/media/manga/"
JS_CTXT          = None
PROCS = []
UA               = { "User-Agent": "Chrome/96.0.4664.110" }
MKDIRP           = not getenv("DRY")
SKIPFETCHEDP = getenv("SKIPFETCHED")

def request(url):
    """Request URL."""
    return req.urlopen(req.Request(url, headers=UA))

def dynasty_get_chapter_list(url):
    """Get the list of chapters in URL.

    Returned value is a dictionary { VOLUME: CHAPTERS } where VOLUME
    is the name of the volume and CHAPTERS is a tuple (NAME, URL)
    where NAME is the name of the chapter and URL is the link to the
    chapter.  If the manga is not divided by volumes, then VOLUME is
    an empty string.

    """
    soup = bs4.BeautifulSoup(request(url), "html.parser")
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
    soup = bs4.BeautifulSoup(request(ch), "html.parser")
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
    soup = bs4.BeautifulSoup(request(url), "html.parser")
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
            JS_CTXT.eval_js_file("./crypto.js")
        return JS_CTXT.eval_js(string)

    soup = bs4.BeautifulSoup(request(ch), "html.parser")
    if js := soup.find("script", string=BATOTO_IMAGE_RE_1):
        # Most of this magic can be figured out by reading the JavaScript
        # sources in a chapter page.  Alternatively, refer to
        # https://github.com/tachiyomiorg/tachiyomi-extensions/blob/master/src/all/batoto/src/eu/kanade/tachiyomi/extension/all/batoto/BatoTo.kt
        js = js.string
        server = re.search(r"(?:const|var) server = ([^;]+);", js).group(1)
        batojs = re.search(r"(?:const|var) batojs = ([^;]+);", js).group(1)
        base = js_eval(f"CryptoJS.AES.decrypt({server} ,{batojs}).toString(CryptoJS.enc.Utf8);").strip("\"")
        return [ base + i for i in json.loads(re.search(r"(?:const|var) images = (\[.*\]);", js).group(1)) ]
    elif js := soup.find("script", string=BATOTO_IMAGE_RE_2):
        # Again, thanks to tachiyomi for showing the light.  It is
        # also easy enough to figure out if you read the JS files.
        js = js.string
        img = re.search(r"(?:const|var) imgHttpLis = ([^;]+);", js).group(1)
        img = json.loads(img)
        batoword = re.search(r"(?:const|var) batoWord = ([^;]+);", js).group(1)
        batopass = re.search(r"(?:const|var) batoPass = ([^;]+);", js).group(1)
        passwd = json.loads(js_eval(f"CryptoJS.AES.decrypt({batoword}, {batopass}).toString(CryptoJS.enc.Utf8);"))
        if len(passwd) != len(img):
            return [ ]
        return [ i + "?" + passwd[n] for n, i in enumerate(img) ]

    return []

def libreddit_get_images(url):
    soup = bs4.BeautifulSoup(request(url), "html.parser")
    gallery = soup.find("div", class_="gallery")
    if not gallery: return []
    return [
        "https://lr.slipfox.xyz" + i["src"]
        for i in gallery.find_all("img")
    ]

def rimgo_get_images(url):
    soup = bs4.BeautifulSoup(request(url), "html.parser")
    imgs = soup.find_all("img", loading="lazy") # Probably will break often.
    if imgs:
        return [
            "https://rimgo.kling.gg" + i["src"] for i in imgs
        ]
    return []

def dankemoe__chapterp(url):
    """Return True if URL is a chapter URL."""
    u = urlparse(url).path.split("/")
    return u[-3].isnumeric()

def dankemoe__fetch_chapter_imgs(ch, slug):
    """Return [ NAME, IMAGES... ] for chapter json CH.
    SLUG is the series SLUG.
    Note that first group translation is always returned.

    """
    group = list(ch["groups"].keys())[0]
    title = ch.get("title", "")
    if title == "":
        title = "Chapter " + i
    else:
        title = "Chapter " + i + ": " + title
    return [
        title,
        *[
            DANKEMOE_MEDIAURL
            + slug \
            + "/chapters/" \
            + ch["folder"] \
            + "/"
            + group
            + "/"
            + i
            for i in ch["groups"][group]
        ]
    ]

def dankemoe_get_chapter_list(url):
    """Return list of [ NAME, IMAGES... ]  for series URL URL.
    NAME is the name of the chapter, and IMAGES... is the URL for
    images of the chapter.

    """
    u = urlparse(url).path.split("/")
    slug = u[-2]
    j = json.loads(request(DANKEMOE_BASE_API_PATH + slug).read())
    ret = []

    for i in j["chapters"]:
        ch = j["chapters"][i]
        ret.append(dankemoe__fetch_chapter_imgs(ch, slug))

    return ret

def dankemoe_get_chapter(url):
    """Return [ NAME, IMAGES... ] for chapter url URL."""
    u = urlparse(url).path.split("/")
    chno = u[-3].replace("-", ".")
    slug = u[-4]

    j = json.loads(request(DANKEMOE_BASE_API_PATH + slug).read())
    ch = j["chapters"][chno]
    return dankemoe__fetch_chapter_imgs(ch, slug)

def do1(image_fun, url, dirname):
    if file_exists_p(dirname) and SKIPFETCHEDP:
            return
    if MKDIRP: mkdir(dirname)

    images = image_fun(url)
    for n, i in enumerate(images):
        _, ext = splitext(i)
        if "?" in ext:
            ext, _, _ = ext.partition("?")
        # For --retry-on-host-error, see https://lists.gnu.org/r/bug-wget/2018-06/msg00012.html
        # and (info "(wget) HTTP Options").  This is for my flaky internet connection.
        print("wget -U -c --retry-on-host-error {} -O {}".format(
            shell_quote(i), shell_quote(f"{dirname}/{n+1:03}{ext}")))

def do(url):
    if "dynasty-scans.com" in url:
        if "chapters" in url:
            do1(dynasty_get_images, url, basename(url))
        else:
            chp = dynasty_get_chapter_list(url)
            nch = 1
            for vol, ch in chp.items():
                for prefix, url in ch:
                    p = multiproc.Process(
                        target=do1,
                        args=(dynasty_get_images, url, (str(nch)+"."+vol+"_" if vol else "")+prefix),
                        name=url)
                    PROCS.append(p)
                    p.start()
                    nch += 1
    elif "lr.slipfox.xyz" in url:
        do1(libreddit_get_images, url, basename(url.strip("/")))
    elif "reddit.com" in url:
        do1(libreddit_get_images,
            re.sub(REDDIT_RE, "https://lr.slipfox.xyz/", url),
            basename(url.strip("/")))
    elif "rimgo.kling.gg" in url:
        if "/a/" in url:
            do1(rimgo_get_images, url, basename(url.strip("/")))
    elif "imgur.com" in url:
        if "/a/" in url:
            do1(rimgo_get_images,
                re.sub(IMGUR_RE, "https://rimgo.kling.gg/", url),
                basename(url.strip("/")))
    elif "cubari.moe/read" in url:
        if "/imgur/" in url and (match := re.match(CUBARI_IMGUR_RE, url)):
            do1(rimgo_get_images, "https://rimgo.kling.gg/a/" + match.group(1), match.group(1))
    elif "danke.moe" in url:
        if not dankemoe__chapterp(url):
            chp = dankemoe_get_chapter_list(url)
            nch = 1
            for name, *imgs in chp:
                p = multiproc.Process(
                    target=do1,
                    args=(lambda x: x, imgs, str(nch)+"."+name),
                    name=name)
                PROCS.append(p)
                p.start()
                nch += 1
        else:
            name, *imgs = dankemoe_get_chapter(url)
            do1(lambda x: x, imgs, name)
    elif "bato.to" in url:
        # There seems to be a race condition somewhere when trying
        # to eval crypto.js so just fetch it earlier when the
        # processes aren't spawned yet.
        if not file_exists_p("./crypto.js"):
            # The same URL tachiyomi uses.
            cryptojs = request("https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.0.0/crypto-js.min.js")
            with open("./crypto.js", "w") as f:
                f.write(cryptojs.read().decode("utf-8"))
        if "chapter" in url:
            do1(batoto_get_images, url, basename(url))
        else:
            chp = batoto_get_chapter_list(url)
            nch = 1
            for name, ch in chp:
                p = multiproc.Process(
                    target=do1,
                    args=(batoto_get_images, ch, str(nch)+"."+name.replace("\n", "", True)),
                    name=ch)
                PROCS.append(p)
                p.start()
                nch += 1

if __name__ == "__main__":
    for i in argv[1:]:
        do(i)
    for p in PROCS: p.join()
