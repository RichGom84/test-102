#!/usr/bin/env python3
"""
장별 무음 MP4 + 장별 나레이션 음성 → 한 편의 영상.

동작 원리
  - 각 장의 애니메이션(2.5배속)은 그대로 재생됩니다.
  - 나레이션이 애니메이션보다 길면, 영상의 마지막 프레임을 복제(정지 화면)해서
    말이 끝날 때까지(+ 여유 시간) 기다립니다.
  - 나레이션이 더 짧으면 영상 길이만큼 무음을 채웁니다.
  - 8개를 순서대로 이어 붙여 output/final.mp4 를 만듭니다.

기본 폴더 구조
  mp4/slide-01.mp4 … mp4/slide-08.mp4   (무음 영상)
  audio/s01.wav … audio/s08.wav         (장별 나레이션, wav 권장 / mp3·m4a 도 가능)
  output/                               (결과물)

사용법
  python merge_narration.py                 # 전체 8장 합치기
  python merge_narration.py --only 3        # 3장만 합쳐서 미리 확인
  python merge_narration.py --tail 0.6      # 말 끝난 뒤 정지 화면 여유(초) 조정
  python merge_narration.py --gap 0.3       # 장과 장 사이 무음 정지 간격(초) 추가

필요: ffmpeg (PATH에 있거나, `pip install imageio-ffmpeg` 로 설치한 번들 사용)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path


# --------------------------------------------------------------------------- #
# ffmpeg / ffprobe 찾기
# --------------------------------------------------------------------------- #
def find_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    sys.exit(
        "ffmpeg 를 찾을 수 없습니다. ffmpeg 를 설치하거나 "
        "`pip install imageio-ffmpeg` 를 실행하세요."
    )


FFMPEG = find_ffmpeg()
FFPROBE = shutil.which("ffprobe")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        sys.exit(f"명령 실패: {' '.join(cmd[:3])} …")
    return proc


# --------------------------------------------------------------------------- #
# 길이 측정
# --------------------------------------------------------------------------- #
def duration_via_ffprobe(path: Path) -> float | None:
    if not FFPROBE:
        return None
    proc = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return float(json.loads(proc.stdout)["format"]["duration"])
    except Exception:
        return None


def duration_via_ffmpeg(path: Path) -> float | None:
    proc = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not m:
        return None
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def duration_via_wave(path: Path) -> float | None:
    if path.suffix.lower() != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


def media_duration(path: Path) -> float:
    for fn in (duration_via_wave, duration_via_ffprobe, duration_via_ffmpeg):
        d = fn(path)
        if d is not None and d > 0:
            return d
    sys.exit(f"길이를 읽을 수 없습니다: {path}")


# --------------------------------------------------------------------------- #
# 파일 찾기
# --------------------------------------------------------------------------- #
AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac")


def find_audio(audio_dir: Path, idx: int) -> Path | None:
    stem = f"s{idx:02d}"
    for ext in AUDIO_EXTS:
        p = audio_dir / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def find_video(mp4_dir: Path, idx: int) -> Path | None:
    for name in (f"slide-{idx:02d}.mp4", f"slide{idx:02d}.mp4", f"s{idx:02d}.mp4", f"{idx:02d}.mp4"):
        p = mp4_dir / name
        if p.exists():
            return p
    return None


# --------------------------------------------------------------------------- #
# 장 하나 합치기
# --------------------------------------------------------------------------- #
def build_part(video: Path, audio: Path, out: Path, tail: float, gap: float,
               fps: int, crf: int) -> float:
    vdur = media_duration(video)
    adur = media_duration(audio)

    # 나레이션 끝 + tail 여유까지는 화면이 남아 있어야 하고,
    # 애니메이션이 더 길면 애니메이션이 끝날 때까지는 기다립니다.
    target = max(vdur, adur + tail) + gap
    pad = max(0.0, target - vdur)

    vf = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={pad:.3f},"
        f"fps={fps},format=yuv420p[v]"
    )
    af = f"[1:a]aresample=48000,apad=whole_dur={target:.3f}[a]"

    cmd = [
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video),
        "-i", str(audio),
        "-filter_complex", f"{vf};{af}",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{target:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)
    print(f"  {video.name:14s} 영상 {vdur:5.2f}s | 음성 {audio.name:8s} {adur:5.2f}s "
          f"→ 결과 {target:5.2f}s (정지 {pad:4.2f}s)")
    return target


def concat_parts(parts: list[Path], out: Path) -> None:
    list_file = out.parent / "concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p.resolve().as_posix()}'\n")
    run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", "-movflags", "+faststart", str(out),
    ])


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mp4", default="mp4", help="무음 영상 폴더 (기본 mp4)")
    ap.add_argument("--audio", default="audio", help="나레이션 음성 폴더 (기본 audio)")
    ap.add_argument("--out", default="output/final.mp4", help="최종 결과 파일")
    ap.add_argument("--count", type=int, default=8, help="장 수 (기본 8)")
    ap.add_argument("--only", type=int, default=None, help="이 장 하나만 합쳐서 확인 (예: --only 3)")
    ap.add_argument("--tail", type=float, default=0.5, help="말 끝난 뒤 정지 화면 여유(초), 기본 0.5")
    ap.add_argument("--gap", type=float, default=0.0, help="각 장 끝에 추가할 무음 간격(초), 기본 0")
    ap.add_argument("--fps", type=int, default=50, help="출력 프레임레이트 (원본 50fps)")
    ap.add_argument("--crf", type=int, default=18, help="x264 화질 (낮을수록 고화질, 기본 18)")
    args = ap.parse_args()

    mp4_dir, audio_dir = Path(args.mp4), Path(args.audio)
    out_path = Path(args.out)
    parts_dir = out_path.parent / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    indices = [args.only] if args.only else list(range(1, args.count + 1))

    # 먼저 빠진 파일이 없는지 전부 점검
    missing = []
    for i in indices:
        if find_video(mp4_dir, i) is None:
            missing.append(f"{mp4_dir}/slide-{i:02d}.mp4")
        if find_audio(audio_dir, i) is None:
            missing.append(f"{audio_dir}/s{i:02d}.wav")
    if missing:
        sys.exit("다음 파일이 없습니다:\n  " + "\n  ".join(missing))

    print(f"ffmpeg: {FFMPEG}")
    parts: list[Path] = []
    total = 0.0
    for i in indices:
        video = find_video(mp4_dir, i)
        audio = find_audio(audio_dir, i)
        assert video and audio
        part = parts_dir / f"part-{i:02d}.mp4"
        total += build_part(video, audio, part, args.tail, args.gap, args.fps, args.crf)
        parts.append(part)

    if args.only:
        final = out_path.parent / f"preview-{args.only:02d}.mp4"
        shutil.copyfile(parts[0], final)
        print(f"\n미리보기 저장: {final}  ({total:.1f}s)")
        return

    concat_parts(parts, out_path)
    print(f"\n완료: {out_path}  (총 {total:.1f}s, {len(parts)}장)")


if __name__ == "__main__":
    main()
