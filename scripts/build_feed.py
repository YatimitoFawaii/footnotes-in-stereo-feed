#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import sys
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


ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
ET.register_namespace("podcast", "https://podcastindex.org/namespace/1.0")
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
ET.register_namespace("googleplay", "http://www.google.com/schemas/play-podcasts/1.0")

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "atom": "http://www.w3.org/2005/Atom",
}


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
    art_dir = DOCS / "art"
    art_dir.mkdir(parents=True, exist_ok=True)
    guid = text_of(item, "guid")
    title = text_of(item, "title", guid or "episode")
    source = EPISODE_IMAGE_SOURCES.get(guid, COVER_SOURCE)
    filename = f"{slugify(title)}.jpg"
    target = art_dir / filename
    source_image = item.find("itunes:image", NS)
    source_url = source_image.get("href", "") if source_image is not None else ""
    if source.exists():
        shutil.copyfile(source, target)
    elif not target.exists() and source_url:
        target.write_bytes(fetch(source_url))
    elif not target.exists() and (art_dir / "cover.jpg").exists():
        shutil.copyfile(art_dir / "cover.jpg", target)
    image_url = f"{PUBLIC_BASE}/art/{filename}"

    itunes_image = item.find("itunes:image", NS)
    if itunes_image is None:
        itunes_image = ET.SubElement(item, f"{{{NS['itunes']}}}image")
    itunes_image.attrib.clear()
    itunes_image.set("href", image_url)


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

    for item in channel.findall("item"):
        rewrite_item_images(item)
        enclosure = item.find("enclosure")
        if enclosure is not None and enclosure.get("url"):
            enclosure.set("url", local_audio_url(item, enclosure))

    feed_path = DOCS / "feed.xml"
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(feed_path, encoding="UTF-8", xml_declaration=True)

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
