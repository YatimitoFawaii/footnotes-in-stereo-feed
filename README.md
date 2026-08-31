# Footnotes in Stereo Feed Mirror

This repo publishes the Footnotes in Stereo episode archive and Apple-facing RSS mirror at:

https://yatimitofawaii.github.io/footnotes-in-stereo-feed/

https://yatimitofawaii.github.io/footnotes-in-stereo-feed/feed.xml

The archive contains transcripts, citations, Patreon links, and matching YouTube
Shorts. It is generated from the production package and only includes episodes
whose member release time has passed. The mirror is generated from the public
Patreon RSS feed and rewrites the feed, show art, episode art, and audio
enclosures to stable GitHub Pages URLs.

Run locally:

```sh
/usr/bin/python3 scripts/build_feed.py
/usr/bin/python3 scripts/build_site.py
```
