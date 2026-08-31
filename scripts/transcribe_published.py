#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = REPO_ROOT.parent
TRANSCRIPTS = REPO_ROOT / "docs" / "transcripts"

EPISODE_AUDIO = {
    1: REPO_ROOT / "docs/audio/how-physics-and-railroads-built-the-circus.m4a",
    2: REPO_ROOT / "docs/audio/the-sophisticated-architectural-matrix-of-genesis.m4a",
    3: REPO_ROOT / "docs/audio/photoshop-from-darkrooms-to-generative-fill.m4a",
    4: REPO_ROOT / "docs/audio/did-the-old-masters-use-tracing-machines.m4a",
    5: REPO_ROOT / "docs/audio/why-division-is-cheaper-than-unity.m4a",
    6: REPO_ROOT / "docs/audio/dada-from-the-trenches-to-internet-memes.m4a",
    7: REPO_ROOT / "docs/audio/how-the-digital-revolution-rewired-music.m4a",
    8: REPO_ROOT / "docs/audio/from-music-boxes-to-jazz-robots.m4a",
    9: REPO_ROOT / "docs/audio/how-hell-became-a-torture-chamber.m4a",
    10: WORKSPACE / "outputs/how-humanity-maps-the-afterlife.m4a",
    11: WORKSPACE / "outputs/how-sewer-socialists-built-modern-america.m4a",
    12: WORKSPACE / "outputs/from-james-madison-to-the-football-field.m4a",
    13: WORKSPACE / "outputs/large-hadron-collider-science-and-doomsday-myths.m4a",
    14: WORKSPACE / "outputs/the-accidental-birth-of-the-cruise-ship.m4a",
    15: WORKSPACE / "outputs/global-gender-variance-from-hijras-to-stonewall.m4a",
    16: WORKSPACE / "outputs/why-our-recorded-music-is-melting.m4a",
    17: WORKSPACE / "outputs/how-the-railroad-conquered-the-clock.m4a",
    18: WORKSPACE / "outputs/the-invention-of-the-normal-human.m4a",
    19: WORKSPACE / "outputs/how-air-conditioning-built-the-sunbelt.m4a",
}


def transcribe_episode(episode: int, source: Path, model: str, force: bool) -> str:
    output = TRANSCRIPTS / f"episode-{episode:02d}.txt"
    if output.exists() and output.stat().st_size > 1000 and not force:
        return f"E{episode}: existing transcript preserved"
    if not source.exists():
        return f"E{episode}: missing audio {source}"

    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"footnotes-e{episode:02d}-") as tmp:
        subprocess.run(
            [
                "whisper", str(source), "--model", model, "--device", "cpu",
                "--fp16", "False", "--language", "en", "--output_format", "txt",
                "--output_dir", tmp, "--verbose", "False", "--threads", "8",
            ],
            check=True,
        )
        generated = Path(tmp) / f"{source.stem}.txt"
        output.write_text(generated.read_text(encoding="utf-8").strip() + "\n", encoding="utf-8")
    return f"E{episode}: wrote {output}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episodes", nargs="*", type=int, default=sorted(EPISODE_AUDIO))
    parser.add_argument("--model", default="small.en")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    for episode in args.episodes:
        print(transcribe_episode(episode, EPISODE_AUDIO[episode], args.model, args.force), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
