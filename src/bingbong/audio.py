from pathlib import Path
import subprocess
import subprocess
from importlib.resources import files

from .paths import OUTDIR

DATA = files("bingbong.data")
POP = str(DATA / "pop.wav")
CHIME = str(DATA / "chime.wav")


def play_file(path: Path) -> None:
    if path.exists():
        subprocess.run(["afplay", str(path)], check=False)
    else:
        print(f"Warning: {path} does not exist.")


def concat(files, output):
    """Concatenate a list of .wav files into a single file using ffmpeg."""
    list_path = OUTDIR / "temp_list.txt"
    with open(list_path, "w", encoding="utf-8") as f:
        f.writelines(f"file '{file}'\n" for file in files)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output)],
        check=True,
    )
    list_path.unlink()


def make_quarters():
    for n in range(1, 4):  # 15, 30, 45
        pops = [POP] * n
        output = OUTDIR / f"quarter_{n}.wav"
        concat(pops, output)


def make_hours():
    for hour in range(1, 13):  # 1 to 12 o'clock
        clusters = []
        remaining = hour
        while remaining >= 3:
            clusters.extend([POP, POP, POP])  # base-3 cluster
            clusters.append("silence.wav")
            remaining -= 3
        if remaining > 0:
            clusters.extend([POP] * remaining)
        output = OUTDIR / f"hour_{hour}.wav"
        concat([CHIME, *clusters], output)


def make_silence():
    """Create a 200ms silence to separate pop clusters."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "0.2",
            str(OUTDIR / "silence.wav"),
        ],
        check=True,
    )


def build_all():
    make_silence()
    make_quarters()
    make_hours()
