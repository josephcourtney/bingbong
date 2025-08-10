"""
Generate prebuilt WAV assets for bingbong using ffmpeg (no pydub/audioop).

This is a maintainer-time script. It rewrites these files in-place under
`src/bingbong/data/`:
  - quarter_1.wav, quarter_2.wav, quarter_3.wav
  - hour_1.wav ... hour_12.wav

Rules:
  quarter_n = silence.wav + (n * pop.wav)
  hour_H    = silence.wav + chime.wav + silence.wav + cluster(H)
  cluster(H)= groups of POPS_PER_CLUSTER pops separated by silence.wav

Usage:
  python scripts/gen_wavs.py
  python scripts/gen_wavs.py --data-dir src/bingbong/data --pops-per-cluster 3
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess  # noqa: S404
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DEFAULT_POPS_PER_CLUSTER = 3


def _repo_data_dir() -> Path:
    # script is .../scripts/gen_wavs.py → repo root is parent of scripts
    root = Path(__file__).resolve().parents[1]
    return root / "src" / "bingbong" / "data"


def _require(paths: Iterable[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        msg = f"Missing input files: {', '.join(missing)}"
        raise SystemExit(msg)


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        msg = "ffmpeg not found on PATH"
        raise SystemExit(msg)
    return path


def _concat_ffmpeg(ffmpeg_bin: str, files: Sequence[Path], out: Path) -> None:
    """Use ffmpeg concat demuxer to join files exactly."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        list_path = Path(td) / "inputs.txt"
        list_path.write_text("".join([f"file '{f.as_posix()}'\n" for f in files]), encoding="utf-8")
        subprocess.run(  # noqa: S603
            [
                ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c",
                "copy",
                str(out),
            ],
            check=True,
        )


def build_quarters(ffmpeg_bin: str, data_dir: Path) -> None:
    silence = data_dir / "silence.wav"
    pop = data_dir / "pop.wav"
    for n in range(1, 4):
        chain = [silence, *([pop] * n)]
        _concat_ffmpeg(ffmpeg_bin, chain, data_dir / f"quarter_{n}.wav")


def build_hours(ffmpeg_bin: str, data_dir: Path, *, pops_per_cluster: int) -> None:
    silence = data_dir / "silence.wav"
    pop = data_dir / "pop.wav"
    chime = data_dir / "chime.wav"

    for hour in range(1, 13):
        # cluster(H) = groups of pops_per_cluster pops, each group followed by silence
        groups = math.ceil(hour / pops_per_cluster)
        cluster: list[Path] = []
        remaining = hour
        for _ in range(groups):
            take = min(remaining, pops_per_cluster)
            cluster.extend([*([pop] * take), silence])
            remaining -= take

        chain = [silence, chime, silence, *cluster]
        _concat_ffmpeg(ffmpeg_bin, chain, data_dir / f"hour_{hour}.wav")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate prebuilt WAVs for bingbong (ffmpeg).")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=_repo_data_dir(),
        help="Path to src/bingbong/data (default: autodetected from repo layout)",
    )
    parser.add_argument(
        "--pops-per-cluster",
        type=int,
        default=DEFAULT_POPS_PER_CLUSTER,
        help="Number of POPs per group when building hour_* files (default: 3)",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    if not data_dir.exists():
        msg = f"data directory does not exist: {data_dir}"
        raise SystemExit(msg)

    # ensure base assets exist
    _require([data_dir / "silence.wav", data_dir / "pop.wav", data_dir / "chime.wav"])

    ffmpeg_bin = _ffmpeg()
    build_quarters(ffmpeg_bin, data_dir)
    build_hours(ffmpeg_bin, data_dir, pops_per_cluster=args.pops_per_cluster)

    print(f"OK: generated quarter_*.wav and hour_*.wav in {data_dir}")


if __name__ == "__main__":
    main()
