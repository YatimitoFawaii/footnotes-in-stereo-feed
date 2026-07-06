#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import sys
from email.utils import format_datetime, parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


SOURCE_RSS = "https://www.patreon.com/public-rss/11912202?show=2250512"
PUBLIC_BASE = "https://yatimitofawaii.github.io/footnotes-in-stereo-feed"
REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
WORKSPACE = Path("/Users/zelda/Documents/Codex/2026-07-02/i")
COVER_SOURCE = WORKSPACE / "outputs" / "footnotes-in-stereo-cover-apple-512.jpg"
EPISODE_IMAGE_SOURCES = {
    "162770841": WORKSPACE / "outputs" / "episode-01-circus-titlecard-apple-512.jpg",
}

EPISODE_DESCRIPTION_OVERRIDES = {
    "162771918": """Genesis is often treated as a beginning, but this episode treats it as an intricate architecture of text, transmission, commentary, translation, and literary design. Mira and Theo move between rabbinic commentary, modern literary analysis, manuscript traditions, chiasmus, and translation debates to ask how the book's structure carries meaning across time. Created with NotebookLM.

Sources cited:
- Bereshit Rabbah | Sefaria Library: https://www.sefaria.org/Bereshit_Rabbah
- Genesis Translation and Commentary / Robert Alter: https://www.staff.ces.funai.edu.ng/papersCollection/Resources/HomePages/genesis_translation_and_commentary.pdf
- Exegesis of Genesis - Asbury Theological Seminary: https://place.asburyseminary.edu/cgi/viewcontent.cgi?article=4174&context=syllabi
- Ramban on Genesis | Sefaria Library: https://www.sefaria.org/Ramban_on_Genesis
- Genesis and Exodus - Reformed Theological Seminary: https://cdn.rts.edu/wp-content/uploads/2019/08/2009_01_2OT711_Genesis_and_Exodus.pdf
- Literary Analysis (Genesis) - Academia.edu: https://www.academia.edu/3787216/Literary_Analysis_Genesis_
- The Theory of Evolution - A Jewish Perspective - Rambam Maimonides Medical Journal: https://www.rmmj.org.il/userimages/9/0/PublishFiles/9Article.pdf
- Rashi on the Torah: What Kind of Commentary Is It? - TheTorah.com: https://www.thetorah.com/article/rashi-on-the-torah-what-kind-of-commentary-is-it
- Chiasmus in the Book of Genesis - BYU ScholarsArchive: https://scholarsarchive.byu.edu/cgi/viewcontent.cgi?article=5113&context=byusq
- The Theology of the Book of Genesis - Cambridge University Press: https://assets.cambridge.org/97805216/85382/frontmatter/9780521685382_frontmatter.pdf
- The Biblical Qumran Scrolls - Eugene Ulrich: https://archive.org/download/TheBiblicalQumranScrolls/61301866-The-Biblical-Qumran-Scrolls-Eugene-Charles-Ulrich.pdf
- Septuagint vs. Masoretic: Which Is More Authentic?: https://stjohnpanamacity.church/wp-content/uploads/Septuagint-vs.-Masoretic.pdf
- Documentary hypothesis - Wikipedia: https://en.wikipedia.org/wiki/Documentary_hypothesis
- The Genre, Historical Context, and Purpose of Genesis 1-11 - Resurrecting Orthodoxy: https://www.joeledmundanderson.com/the-genre-historical-context-and-purpose-of-genesis-1-11/
- Rethinking Genesis 1: How Translators Changed the First Verse | Genesis Analysis Ep. 1: https://www.youtube.com/results?search_query=Rethinking+Genesis+1+How+Translators+Changed+the+First+Verse""",
}


ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
ET.register_namespace("podcast", "https://podcastindex.org/namespace/1.0")
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
ET.register_namespace("googleplay", "http://www.google.com/schemas/play-podcasts/1.0")

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "br", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "episode"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "FootnotesInStereoFeedMirror/1.0 (+https://www.patreon.com/collection/2250512)",
            "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def text_of(parent: ET.Element, tag: str, fallback: str = "") -> str:
    node = parent.find(tag)
    if node is None or node.text is None:
        return fallback
    return node.text


def set_or_add(parent: ET.Element, tag: str, text: str) -> ET.Element:
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    node.text = text
    return node


def set_or_insert_before_first_item(parent: ET.Element, tag: str, text: str) -> ET.Element:
    node = parent.find(tag)
    if node is None:
        node = ET.Element(tag)
        children = list(parent)
        item_index = next((index for index, child in enumerate(children) if child.tag == "item"), len(children))
        parent.insert(item_index, node)
    node.text = text
    return node


def normalize_pubdate(parent: ET.Element) -> None:
    for tag in ("pubDate", "lastBuildDate"):
        node = parent.find(tag)
        if node is not None and node.text:
            try:
                node.text = format_datetime(parsedate_to_datetime(node.text))
            except Exception:
                pass


def clean_description(value: str) -> tuple[str, str]:
    decoded = unescape(value or "")
    while unescape(decoded) != decoded:
        decoded = unescape(decoded)
    extractor = TextExtractor()
    extractor.feed(decoded)
    plain = extractor.text() or decoded.strip()
    html = decoded
    return plain, html


def rewrite_atom_self(channel: ET.Element) -> None:
    atom_link = channel.find("atom:link", NS)
    if atom_link is None:
        atom_link = ET.SubElement(channel, f"{{{NS['atom']}}}link")
    atom_link.attrib.clear()
    atom_link.set("href", f"{PUBLIC_BASE}/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")


def rewrite_channel_images(channel: ET.Element) -> None:
    art_dir = DOCS / "art"
    art_dir.mkdir(parents=True, exist_ok=True)
    cover_target = art_dir / "cover.jpg"
    source_image = channel.find("itunes:image", NS)
    source_url = source_image.get("href", "") if source_image is not None else ""
    if COVER_SOURCE.exists():
        shutil.copyfile(COVER_SOURCE, cover_target)
    elif not cover_target.exists() and source_url:
        cover_target.write_bytes(fetch(source_url))
    cover_url = f"{PUBLIC_BASE}/art/cover.jpg"

    itunes_image = channel.find("itunes:image", NS)
    if itunes_image is None:
        itunes_image = ET.SubElement(channel, f"{{{NS['itunes']}}}image")
    itunes_image.attrib.clear()
    itunes_image.set("href", cover_url)

    image = channel.find("image")
    if image is None:
        image = ET.SubElement(channel, "image")
    set_or_add(image, "url", cover_url)
    set_or_add(image, "title", text_of(channel, "title", "Footnotes in Stereo"))
    set_or_add(image, "link", text_of(channel, "link", "https://www.patreon.com/collection/2250512"))


def local_audio_url(item: ET.Element, enclosure: ET.Element) -> str:
    audio_dir = DOCS / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    guid = text_of(item, "guid")
    title = text_of(item, "title", guid or "episode")
    parsed_path = urllib.parse.urlparse(enclosure.get("url", "")).path
    suffix = Path(parsed_path).suffix or ".m4a"
    filename = f"{slugify(title)}{suffix}"
    target = audio_dir / filename
    if not target.exists():
        target.write_bytes(fetch(enclosure.get("url", "")))
    enclosure.set("length", str(target.stat().st_size))
    return f"{PUBLIC_BASE}/audio/{filename}"


def rewrite_item_images(item: ET.Element) -> None:
    itunes_image = item.find("itunes:image", NS)
    if itunes_image is not None:
        item.remove(itunes_image)


def build() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    rss_bytes = fetch(SOURCE_RSS)
    root = ET.fromstring(rss_bytes)
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("RSS channel not found")

    rewrite_atom_self(channel)
    rewrite_channel_images(channel)
    set_or_add(channel, "generator", "Footnotes in Stereo feed mirror")
    channel_description = text_of(channel, "description")
    set_or_insert_before_first_item(channel, f"{{{NS['itunes']}}}summary", channel_description)
    set_or_insert_before_first_item(channel, f"{{{NS['itunes']}}}subtitle", "Conversational research deep dives with Mira Vale and Theo Arlen.")
    normalize_pubdate(channel)

    for item in channel.findall("item"):
        rewrite_item_images(item)
        item_description = item.find("description")
        guid = text_of(item, "guid")
        if item_description is not None and item_description.text:
            plain_description, _html_description = clean_description(item_description.text)
            item_description.text = plain_description
        if (
            item_description is not None
            and guid in EPISODE_DESCRIPTION_OVERRIDES
            and (item_description.text or "").strip().lower() in {"", "<html></html>", "html"}
        ):
            item_description.text = EPISODE_DESCRIPTION_OVERRIDES[guid]
        set_or_add(item, f"{{{NS['itunes']}}}author", text_of(channel, f"{{{NS['itunes']}}}author", "Mira Vale and Theo Arlen"))
        set_or_add(item, f"{{{NS['itunes']}}}explicit", "false")
        normalize_pubdate(item)
        enclosure = item.find("enclosure")
        if enclosure is not None and enclosure.get("url"):
            enclosure.set("url", local_audio_url(item, enclosure))

    feed_path = DOCS / "feed.xml"
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(feed_path, encoding="UTF-8", xml_declaration=True)
    feed_text = feed_path.read_text(encoding="UTF-8")
    feed_text = feed_text.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>', 1)
    feed_text = feed_text.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")
    feed_path.write_text(feed_text, encoding="UTF-8")

    (DOCS / "index.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Footnotes in Stereo RSS Feed</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <h1>Footnotes in Stereo</h1>
  <p>Podcast RSS feed: <a href="feed.xml">feed.xml</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )

    print(feed_path)


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        raise
