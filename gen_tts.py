#!/usr/bin/env python3
"""
narration.md 의 8장 대본을 Qwen3-TTS 음성 복제로 읽어 audio/s01.wav ~ s08.wav 를 만듭니다.

근거 문서: https://github.com/QwenLM/Qwen3-TTS (README의 Voice Clone 예제)
  - 패키지:  pip install -U qwen-tts
  - 모델:    Qwen/Qwen3-TTS-12Hz-1.7B-Base  (작은 버전: Qwen/Qwen3-TTS-12Hz-0.6B-Base)
  - 호출:    model.generate_voice_clone(text=..., language="Korean", ref_audio=..., ref_text=...)
  - ref_text 는 참조 음성에서 실제로 말한 내용. 생략하면 x_vector_only_mode=True 로 돌아가며
    품질이 떨어질 수 있다고 문서에 적혀 있습니다.

사용법
  python gen_tts.py --dry-run                 # 모델 없이 대본 파싱 결과만 확인
  python gen_tts.py --only 1 --ref-slide 2    # 1장만 생성, 참조 샘플은 2장을 읽은 녹음
  python gen_tts.py --ref-slide 2             # 8장 전체 생성
  python gen_tts.py --ref-text "샘플에서 읽은 문장 그대로"   # 대본이 아닌 문장을 읽었을 때

기본 경로
  참조 음성: ref/my_voice.wav      출력: audio/sNN.wav
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SECTION_RE = re.compile(r"^##\s*(\d+)장\b.*?→\s*(s\d{2})\.wav", re.M)


# --------------------------------------------------------------------------- #
# 대본 파싱
# --------------------------------------------------------------------------- #
def parse_script(md_path: Path) -> dict[int, str]:
    """{장 번호: 대본 본문} 을 돌려줍니다. 제목 줄과 '---' 이후 메모는 제외합니다."""
    text = md_path.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        sys.exit(f"{md_path} 에서 '## N장 … → sNN.wav' 형식의 섹션을 찾지 못했습니다.")
    result: dict[int, str] = {}
    for k, m in enumerate(matches):
        start = m.end()
        end = matches[k + 1].start() if k + 1 < len(matches) else len(text)
        body = text[start:end]
        body = body.split("\n---", 1)[0]          # 수정 메모 구간 제거
        lines = [ln.strip() for ln in body.splitlines()]
        lines = [ln for ln in lines if ln and not ln.startswith("#")]
        result[int(m.group(1))] = " ".join(lines)
    return result


# --------------------------------------------------------------------------- #
# 참조 음성 로드 (wav 가 아니면 ffmpeg 로 변환)
# --------------------------------------------------------------------------- #
def find_ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def load_ref_audio(path: Path):
    """(numpy_array, sample_rate) 튜플로 돌려줍니다. 문서상 ref_audio 가 이 형식을 받습니다."""
    import soundfile as sf

    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    except Exception:
        ff = find_ffmpeg()
        if not ff:
            sys.exit(f"{path} 를 읽을 수 없고 ffmpeg 도 없습니다. wav 로 변환해서 다시 넣어 주세요.")
        tmp = Path(tempfile.mkdtemp()) / "ref_converted.wav"
        subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(path),
                        "-ac", "1", "-ar", "24000", "-sample_fmt", "s16", str(tmp)], check=True)
        data, sr = sf.read(str(tmp), dtype="float32", always_2d=False)
    if getattr(data, "ndim", 1) > 1:
        data = data.mean(axis=1)                  # 스테레오 → 모노
    dur = len(data) / float(sr)
    if dur < 5:
        print(f"경고: 참조 음성이 {dur:.1f}초로 짧습니다. 10~20초를 권장합니다.")
    if dur > 40:
        print(f"경고: 참조 음성이 {dur:.1f}초로 깁니다. 앞 30초만 사용합니다.")
        data = data[: int(30 * sr)]
    return data, sr, dur


# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", default="narration.md")
    ap.add_argument("--ref", default="ref/my_voice.wav", help="내 목소리 샘플")
    ap.add_argument("--ref-text", default=None, help="샘플에서 말한 내용(문장 그대로)")
    ap.add_argument("--ref-slide", type=int, default=None,
                    help="샘플이 대본의 N장을 읽은 것이면 N. 그 장의 대본을 ref_text 로 씁니다.")
    ap.add_argument("--model", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    ap.add_argument("--device", default="auto", help="auto | cuda:0 | cpu")
    ap.add_argument("--language", default="Korean")
    ap.add_argument("--out", default="audio")
    ap.add_argument("--only", type=int, default=None, help="이 장만 생성")
    ap.add_argument("--dry-run", action="store_true", help="모델을 로드하지 않고 대본 파싱만 출력")
    args = ap.parse_args()

    script = parse_script(Path(args.script))
    targets = [args.only] if args.only else sorted(script)
    for i in targets:
        if i not in script:
            sys.exit(f"{i}장이 대본에 없습니다. 있는 장: {sorted(script)}")

    if args.dry_run:
        for i in targets:
            print(f"[{i}장 → s{i:02d}.wav] ({len(script[i])}자)\n{script[i]}\n")
        return

    # ---- 참조 텍스트 결정 ------------------------------------------------- #
    ref_text = args.ref_text
    if ref_text is None and args.ref_slide is not None:
        ref_text = script[args.ref_slide]
    x_vector_only = ref_text is None
    if x_vector_only:
        print("참고: --ref-text / --ref-slide 가 없어 x_vector_only_mode=True 로 생성합니다. "
              "문서상 품질이 떨어질 수 있으니, 샘플에서 읽은 문장을 알려주면 더 좋습니다.")

    ref_path = Path(args.ref)
    if not ref_path.exists():
        sys.exit(f"참조 음성이 없습니다: {ref_path}\n조용한 곳에서 대본 한 장을 10~20초 읽어 이 경로에 넣어 주세요.")

    # ---- 의존성 ----------------------------------------------------------- #
    try:
        import torch
        import soundfile as sf
        from qwen_tts import Qwen3TTSModel
    except ImportError as e:
        sys.exit(f"패키지가 없습니다 ({e}). 먼저:  pip install -r requirements-tts.txt")

    ref_audio, ref_sr, ref_dur = load_ref_audio(ref_path)
    print(f"참조 음성: {ref_path} ({ref_dur:.1f}s, {ref_sr}Hz)")

    # ---- 장치 / 정밀도 ---------------------------------------------------- #
    device = args.device
    if device == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    if device.startswith("cuda"):
        dtype = torch.bfloat16
        try:
            import flash_attn  # noqa: F401
            attn = "flash_attention_2"
        except ImportError:
            attn = "sdpa"
    else:
        dtype = torch.float32
        attn = "sdpa"
        print("경고: GPU 가 없어 CPU 로 실행합니다. 매우 느리거나 메모리가 부족할 수 있습니다. "
              "그럴 땐 --model Qwen/Qwen3-TTS-12Hz-0.6B-Base 를 시도하세요.")
    print(f"모델 로드: {args.model} (device={device}, dtype={dtype}, attn={attn})")

    model = Qwen3TTSModel.from_pretrained(
        args.model, device_map=device, dtype=dtype, attn_implementation=attn,
    )

    # ---- 생성 --------------------------------------------------------------- #
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in targets:
        text = script[i]
        kwargs = dict(text=text, language=args.language, ref_audio=(ref_audio, ref_sr))
        if x_vector_only:
            kwargs["x_vector_only_mode"] = True
        else:
            kwargs["ref_text"] = ref_text
        print(f"\n[{i}장] {len(text)}자 생성 중…")
        wavs, sr = model.generate_voice_clone(**kwargs)
        out = out_dir / f"s{i:02d}.wav"
        sf.write(str(out), wavs[0], sr, subtype="PCM_16")
        dur = len(wavs[0]) / float(sr)
        rows.append((i, out, dur))
        print(f"  저장: {out}  ({dur:.1f}s, {sr}Hz)")

    print("\n장 | 파일          | 길이")
    for i, out, dur in rows:
        print(f"{i:>2} | {out.name:13s} | {dur:5.1f}s")
    print("\n다음:  python merge_narration.py" + (f" --only {args.only}" if args.only else ""))


if __name__ == "__main__":
    main()
