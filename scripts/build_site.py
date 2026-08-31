#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"
WORKSPACE = REPO_ROOT.parent
PACKAGE = WORKSPACE / "outputs/patreon-podcast-draft-package.md"
SOCIAL_PLAN = WORKSPACE / "outputs/social-release-plan.md"
CATALOG = REPO_ROOT / "data" / "episode-catalog.json"
PACIFIC = ZoneInfo("America/Los_Angeles")
YOUTUBE_FALLBACK = {
    1: "https://www.youtube.com/shorts/tuwygTciYks",
    2: "https://www.youtube.com/shorts/zx8nX8PuVso",
    3: "https://www.youtube.com/shorts/YJf1v1lxEhc",
    4: "https://www.youtube.com/shorts/VUNGd9b-h-g",
    5: "https://www.youtube.com/shorts/ze-vRMNtVEM",
    6: "https://www.youtube.com/shorts/jgQkNHCqfXI",
    7: "https://www.youtube.com/shorts/3T4bVHmFGgI",
    8: "https://www.youtube.com/shorts/1-PyGqH5UrU",
    9: "https://www.youtube.com/shorts/S5nJJoRqBp8",
    10: "https://www.youtube.com/shorts/OU1K7U80A5Y",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def parse_release(value: str) -> datetime | None:
    if not value or "Patreon-only" in value:
        return None
    value = re.sub(r"^[A-Za-z]+,\s*", "", value.strip())
    value = re.sub(r"\s+(PDT|PST)$", "", value)
    try:
        return datetime.strptime(value, "%B %d, %Y, %I:%M %p").replace(tzinfo=PACIFIC)
    except ValueError:
        return None


def parse_package() -> dict[int, dict]:
    text = PACKAGE.read_text(encoding="utf-8")
    episodes: dict[int, dict] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        number = int(cells[0])
        url_match = re.search(r"https?://[^\s|]+", cells[1])
        if url_match is None:
            continue
        member_release = parse_release(cells[2])
        public_release = parse_release(cells[3])
        episodes[number] = {
            "number": number,
            "patreon_url": re.sub(r"/edit(?:\?.*)?$", "", url_match.group(0)),
            "member_release": member_release,
            "public_release": public_release,
            "exclusive": public_release is None,
        }

    matches = list(re.finditer(r"^## Episode (\d+)(?:\s+-[^\n]+)?\s*$", text, re.MULTILINE))
    for index, match in enumerate(matches):
        number = int(match.group(1))
        if number not in episodes:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end():end]
        title = re.search(r"\*\*Title:\*\*\s*(.+)", section)
        description = re.search(r"\*\*Description:\*\*\s*\n(.*?)(?=\n\*\*Sources cited:\*\*)", section, re.S)
        sources = re.search(r"\*\*Sources cited:\*\*\s*\n(.*?)(?=\n## |\Z)", section, re.S)
        if title:
            episodes[number]["title"] = title.group(1).strip()
        if description:
            episodes[number]["description"] = description.group(1).strip()
        parsed_sources = []
        if sources:
            for line in sources.group(1).splitlines():
                source = re.match(r"-\s+(.+?):\s+(https?://\S+)", line.strip())
                if source:
                    parsed_sources.append({"title": source.group(1), "url": source.group(2)})
        episodes[number]["sources"] = parsed_sources
    return episodes


def load_catalog() -> dict[int, dict]:
    if PACKAGE.exists():
        episodes = parse_package()
        CATALOG.parent.mkdir(parents=True, exist_ok=True)
        serializable = []
        for episode in episodes.values():
            row = dict(episode)
            for key in ("member_release", "public_release"):
                row[key] = row[key].isoformat() if row[key] else None
            serializable.append(row)
        CATALOG.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        return episodes
    if not CATALOG.exists():
        raise FileNotFoundError("No local production package or checked-in episode catalog found")
    episodes = {}
    for row in json.loads(CATALOG.read_text(encoding="utf-8")):
        for key in ("member_release", "public_release"):
            row[key] = datetime.fromisoformat(row[key]) if row.get(key) else None
        episodes[row["number"]] = row
    return episodes


def youtube_urls() -> dict[int, str]:
    urls = dict(YOUTUBE_FALLBACK)
    if SOCIAL_PLAN.exists():
        plan = SOCIAL_PLAN.read_text(encoding="utf-8")
        for number, url in re.findall(r"Episode\s+(\d+):\s*`?(https://www\.youtube\.com/shorts/[\w-]+)", plan):
            urls[int(number)] = url
    return urls


def find_art(number: int) -> str:
    candidates = []
    for pattern in (f"episode-{number:02d}-*titlecard*.png", f"episode-{number:02d}-*titlecard*.jpg"):
        candidates.extend((WORKSPACE / "outputs").glob(pattern))
    if not candidates:
        return "art/cover.jpg"
    source = sorted(candidates, key=lambda path: ("instagram" in path.name, len(path.name)))[0]
    target_dir = DOCS / "episodes" / "art"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"episode-{number:02d}{source.suffix.lower()}"
    shutil.copyfile(source, target)
    return str(target.relative_to(DOCS))


def episode_card(episode: dict) -> str:
    badge = "Patreon bonus" if episode["exclusive"] else "Public episode"
    youtube = f'<a class="button secondary" href="{html.escape(episode.get("youtube_url", ""))}">Watch the Short</a>' if episode.get("youtube_url") else ""
    return f'''<article class="episode-card">
      <a href="episodes/{episode['slug']}.html"><img src="{episode['art']}" alt="Episode {episode['number']} titlecard" loading="lazy"></a>
      <div class="episode-card-body"><span class="eyebrow">E{episode['number']} · {badge}</span>
      <h2><a href="episodes/{episode['slug']}.html">{html.escape(episode['title'])}</a></h2>
      <p>{html.escape(episode.get('description', '').split('\n\n')[0])}</p>
      <div class="actions"><a class="button" href="{html.escape(episode['patreon_url'])}">Listen on Patreon</a>{youtube}</div></div>
    </article>'''


def episode_page(episode: dict) -> str:
    transcript_path = DOCS / "transcripts" / f"episode-{episode['number']:02d}.txt"
    transcript = transcript_path.read_text(encoding="utf-8").strip() if transcript_path.exists() else "Transcript processing. Check back shortly."
    source_items = "".join(f'<li><a href="{html.escape(source["url"])}">{html.escape(source["title"])}</a></li>' for source in episode["sources"])
    youtube = f'<a class="button secondary" href="{html.escape(episode.get("youtube_url", ""))}">Watch the Short</a>' if episode.get("youtube_url") else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>E{episode['number']}: {html.escape(episode['title'])} | Footnotes in Stereo</title><link rel="stylesheet" href="../site.css"></head>
<body><header class="site-header"><a class="brand" href="../"><img src="../art/cover.jpg" alt="Footnotes in Stereo"><span>Footnotes in Stereo<small>Fake voices, real facts.</small></span></a></header>
<main class="episode-page"><a class="back" href="../">All episodes</a><div class="episode-hero"><img src="../{episode['art']}" alt="Episode {episode['number']} titlecard"><div><span class="eyebrow">Episode {episode['number']} · {'Patreon bonus' if episode['exclusive'] else 'Public episode'}</span><h1>{html.escape(episode['title'])}</h1><p>{html.escape(episode.get('description', ''))}</p><div class="actions"><a class="button" href="{html.escape(episode['patreon_url'])}">Listen on Patreon</a>{youtube}</div></div></div>
<section><h2>Sources</h2><ol class="sources">{source_items or '<li>Source list is being verified.</li>'}</ol></section>
<section><h2>Transcript</h2><p class="transcript-note">Machine transcript; lightly formatted and subject to correction.</p><div class="transcript">{html.escape(transcript)}</div></section></main>
<footer>Created with Gemini Notebook. The conversation and voices in each episode were generated with Gemini Notebook.</footer></body></html>'''


def main() -> int:
    now = datetime.now(PACIFIC)
    episodes = load_catalog()
    videos = youtube_urls()
    visible = []
    for episode in episodes.values():
        release = episode["member_release"]
        if release is None or release > now or not episode.get("title"):
            continue
        episode["slug"] = f"episode-{episode['number']:02d}-{slugify(episode['title'])}"
        episode["youtube_url"] = videos.get(episode["number"], "")
        episode["art"] = find_art(episode["number"])
        visible.append(episode)
    visible.sort(key=lambda item: item["number"], reverse=True)

    episode_dir = DOCS / "episodes"
    episode_dir.mkdir(parents=True, exist_ok=True)
    for old_page in episode_dir.glob("episode-*.html"):
        old_page.unlink()
    for episode in visible:
        (episode_dir / f"{episode['slug']}.html").write_text(episode_page(episode), encoding="utf-8")

    cards = "\n".join(episode_card(episode) for episode in visible)
    index = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Transcripts and sources for Footnotes in Stereo. Fake voices, real facts."><title>Footnotes in Stereo | Episode Archive</title><link rel="stylesheet" href="site.css"></head>
<body><header class="site-header"><a class="brand" href="./"><img src="art/cover.jpg" alt="Footnotes in Stereo"><span>Footnotes in Stereo<small>Fake voices, real facts.</small></span></a><nav><a href="feed.xml">RSS</a><a href="https://www.patreon.com/c/podcasts/2250512">Patreon</a><a href="https://www.youtube.com/@footnotesinstereo">YouTube</a></nav></header>
<main><section class="intro"><span class="eyebrow">Episode archive</span><h1>Follow the footnotes.</h1><p>Transcripts, citations, and listening links for every released episode of Footnotes in Stereo.</p><label class="search"><span>Search episodes</span><input id="episode-search" type="search" placeholder="Topic, title, or episode number"></label></section><section id="episode-grid" class="episode-grid">{cards}</section><p id="empty-state" hidden>No released episodes match that search.</p></main>
<footer><strong>Fake voices, real facts.</strong> Created with Gemini Notebook. The conversation and voices in each episode were generated with Gemini Notebook.</footer><script src="site.js"></script></body></html>'''
    (DOCS / "index.html").write_text(index, encoding="utf-8")
    (DOCS / "episodes.json").write_text(json.dumps(visible, default=str, indent=2), encoding="utf-8")
    print(f"Built archive with {len(visible)} released episodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
