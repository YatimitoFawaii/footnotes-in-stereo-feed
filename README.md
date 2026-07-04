# Footnotes in Stereo Feed Mirror

This repo publishes an Apple-facing RSS mirror for Footnotes in Stereo at:

https://yatimitofawaii.github.io/footnotes-in-stereo-feed/feed.xml

The mirror is generated from the public Patreon RSS feed and rewrites the feed,
show art, episode art, and audio enclosures to stable GitHub Pages URLs.

Run locally:

```sh
/usr/bin/python3 scripts/build_feed.py
```

