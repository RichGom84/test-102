# 클로드 코드 지시문 — 나레이션 생성 후 영상 합치기

아래 내용을 통째로 복사해서 이 저장소 폴더에서 클로드 코드에 붙여넣으세요.
(사전 준비: `ref/my_voice.wav` 에 본인 목소리 샘플 10~20초를 넣어 둘 것. 조용한 곳에서 `narration.md` 아무 장이나 또렷하게 읽은 녹음이면 됩니다.)

---

이 저장소는 카드뉴스 8장짜리 무음 영상(`mp4/slide-01.mp4` ~ `slide-08.mp4`)에 내 목소리로 만든 나레이션을 입혀 한 편의 영상으로 만드는 프로젝트다. 아래 순서대로 진행해라. 각 단계가 끝날 때마다 무엇을 했고 결과가 어땠는지 짧게 보고해라.

## 0. 현황 파악

- `narration.md`(8장 대본), `merge_narration.py`(합치기 스크립트), `mp4/`(무음 영상 8개), `ref/my_voice.wav`(내 목소리 샘플)가 있는지 확인해라.
- `ref/my_voice.wav` 가 없으면 멈추고 나에게 요청해라. 다른 목소리로 대체하지 마라.
- ffmpeg 가 있는지 확인해라. 없으면 `pip install imageio-ffmpeg` 로 번들 버전을 설치해라. (스크립트가 자동으로 찾는다.)

## 1. Qwen TTS 음성 복제 세팅 (추측 금지)

- 생성 스크립트 `gen_tts.py` 와 의존성 목록 `requirements-tts.txt`, 세팅 메모 `tts_setup_notes.md` 가 이미 있다. 이 셋은 공식 README(https://github.com/QwenLM/Qwen3-TTS)를 보고 만든 것이다.
- **먼저 공식 문서(GitHub README와 Hugging Face 모델 카드)를 다시 열어, `gen_tts.py` 가 쓰는 모델명 · `Qwen3TTSModel.from_pretrained` 인자 · `generate_voice_clone` 인자가 현재 문서와 같은지 대조해라.** 다르면 문서에 맞게 `gen_tts.py` 를 고치고, 무엇을 왜 바꿨는지 `tts_setup_notes.md` 에 추가해라. 기억이나 추측으로 고치지 마라.
- `pip install -r requirements-tts.txt` 로 설치해라. torch 는 이 PC의 GPU에 맞는 빌드가 필요하면 https://pytorch.org 안내대로 먼저 설치해라.
- GPU 유무를 확인해라.
  - GPU가 있으면 그대로 진행한다. VRAM이 부족해 로드가 실패하면 `--model Qwen/Qwen3-TTS-12Hz-0.6B-Base` 로 바꿔 시도해라.
  - GPU가 없으면 `gen_tts.py` 가 CPU로 시도한다. 1장 생성에 10분 넘게 걸리거나 메모리 오류가 나면 멈추고, 클라우드 API(Alibaba Cloud Model Studio) 방식으로 전환할지 나에게 물어라. 그 경우 필요한 API 키 이름을 알려주고 키를 받을 때까지 기다려라. 키를 코드에 하드코딩하지 마라.
- 참조 음성 `ref/my_voice.wav` 가 wav 가 아니면(m4a, mp3 등) 스크립트가 ffmpeg 로 자동 변환한다. 변환이 실패하면 ffmpeg 로 직접 wav 로 바꿔라.
- 나에게 **샘플에서 대본의 몇 장을 읽었는지** 물어라. N장이면 `--ref-slide N` 을, 대본이 아닌 문장을 읽었으면 `--ref-text "그 문장"` 을 쓴다. 이 값이 없으면 품질이 떨어진다고 문서에 적혀 있다.

## 2. 1개만 먼저 생성해서 확인

- 8개를 한 번에 돌리지 말고 **1장(`s01.wav`)만 먼저 생성**해라.  예: `python gen_tts.py --only 1 --ref-slide 2`
- 생성 후 길이(초)를 출력하고, `python merge_narration.py --only 1` 로 미리보기 `output/preview-01.mp4` 를 만들어라.
- 여기서 멈추고 나에게 "1장 미리보기가 준비됐다"고 알려라. 내가 들어보고 목소리·속도·발음이 괜찮은지 답할 때까지 다음 단계로 가지 마라.

## 3. 나머지 7개 생성

- 내가 OK 하면 `python gen_tts.py --ref-slide N` 으로 8장 전체를 생성해라. (1장은 덮어써도 된다.)
- 각 파일의 길이를 표로 보여줘라. `narration.md` 의 예상 시간과 2배 이상 차이 나는 장이 있으면 알려라. (TTS가 문장을 빼먹었거나 반복했을 가능성이 있다.)
- 특정 장에서 발음이 이상하다고 내가 말하면, `narration.md` 의 그 장 문구만 고쳐서 `--only N` 으로 해당 파일만 다시 생성해라.

## 4. 전체 합치기

- `python merge_narration.py` 를 실행해서 `output/final.mp4` 를 만들어라.
- 결과 파일의 총 길이, 해상도(1080x1350이어야 함), 오디오 유무를 ffmpeg 로 확인해서 보고해라.
- 장 사이가 너무 붙어 있으면 `--gap 0.3` 같은 옵션으로 다시 합칠 수 있다고 알려줘라. 나에게 묻지 말고 기본값으로 먼저 만들어라.

## 지켜야 할 것

- `mp4/` 안의 원본 영상은 수정하지 마라. 결과물은 전부 `output/` 에만 써라.
- `ref/`, `audio/`, `output/` 폴더는 커밋하지 마라(`.gitignore` 에 이미 있다). 코드와 문서만 커밋해라.
- 모델 다운로드나 API 호출에 돈이 드는 경우, 예상 비용을 먼저 말하고 진행해라.
- 확실하지 않은 건 확실하지 않다고 말해라.
