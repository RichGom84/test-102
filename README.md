# 카드뉴스 나레이션 키트 — 구글 Home MCP 얼리액세스 (8장)

효과음 대신 **내 목소리 나레이션**을 입혀 카드뉴스 영상을 만드는 작업 세트입니다.
애니메이션(2.5배속)은 그대로 두고, 말이 끝날 때까지 각 장의 마지막 화면이 정지해 있다가 다음 장으로 넘어갑니다.

## 구성

| 파일 | 역할 |
| --- | --- |
| `mp4/slide-01.mp4` ~ `slide-08.mp4` | 효과음을 뺀 무음 장별 영상 (1080x1350, 50fps) |
| `narration.md` | 8장 대본. 장마다 `[구간·예상시간]` 표기, 빠른 말투 기준 총 약 70초 |
| `gen_tts.py` | Qwen3-TTS 음성 복제로 대본 8장을 `audio/s01~s08.wav` 로 생성 (`requirements-tts.txt`, `tts_setup_notes.md` 참고) |
| `merge_narration.py` | 장별 음성 길이에 맞춰 영상 끝 프레임을 늘려 합치는 ffmpeg 스크립트 |
| `CLAUDE_CODE_PROMPT.md` | 클로드 코드에 붙여넣을 지시문 (Qwen TTS 음성 복제 → 8개 생성 → 1개 확인 후 합체) |

## 사용 순서

1. `ref/my_voice.wav` 에 본인 목소리 샘플 10~20초를 넣습니다. 조용한 곳에서 대본 아무 장이나 또렷하게 읽으면 복제 품질이 좋습니다.
2. 클로드 코드를 이 폴더에서 열고 `CLAUDE_CODE_PROMPT.md` 내용을 붙여넣습니다.
3. 클로드 코드가 `audio/s01.wav` ~ `s08.wav` 를 만들고 `output/final.mp4` 로 합칩니다.

클로드 코드 없이 직접 돌리려면 (GPU 권장):

```bash
pip install -r requirements-tts.txt
python gen_tts.py --only 1 --ref-slide 2   # 샘플이 2장을 읽은 녹음일 때, 1장만 먼저 생성
python merge_narration.py --only 1         # 미리보기 → output/preview-01.mp4
python gen_tts.py --ref-slide 2            # 8장 전체 생성
python merge_narration.py                  # 전체 합치기 → output/final.mp4
```

옵션: `--tail 0.5`(말 끝난 뒤 정지 여유, 초), `--gap 0.3`(장 사이 간격, 초), `--crf 18`(화질).

## 폴더 구조

```
mp4/      무음 영상 (커밋됨)
ref/      my_voice.wav  (커밋 안 함)
audio/    s01.wav ~ s08.wav  (커밋 안 함)
output/   parts/, preview-XX.mp4, final.mp4  (커밋 안 함)
```
