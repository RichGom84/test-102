# Qwen TTS 세팅 메모

2026-09-17 기준, 공식 README(https://github.com/QwenLM/Qwen3-TTS)에서 확인한 내용입니다.
Hugging Face 모델 카드는 이 세션의 네트워크 정책으로 열 수 없어 확인하지 못했습니다. 로컬에서 실행 전에 한 번 더 대조하세요.

## 확인한 사실

- 설치: `pip install -U qwen-tts`
- 음성 복제용 모델: `Qwen/Qwen3-TTS-12Hz-1.7B-Base` (작은 버전 `Qwen/Qwen3-TTS-12Hz-0.6B-Base`)
- 지원 언어: Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian
- 호출 예제 (README 원문):

```python
import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel

model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
    device_map="cuda:0",
    dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",
)
wavs, sr = model.generate_voice_clone(
    text="...",
    language="English",
    ref_audio=ref_audio,     # 파일 경로, URL, base64, 또는 (numpy_array, sample_rate)
    ref_text=ref_text,       # 참조 음성에서 실제로 말한 내용
)
sf.write("output_voice_clone.wav", wavs[0], sr)
```

- `ref_text` 는 기본적으로 필요. `x_vector_only_mode=True` 를 주면 생략 가능하지만 품질이 떨어질 수 있다고 명시.
- FlashAttention 2 는 권장 사항. 없으면 `attn_implementation="sdpa"` 로 대체 (gen_tts.py 가 자동 판단).
- CPU 실행은 README에 언급이 없음. gen_tts.py 는 GPU가 없으면 CPU + float32 로 시도하되 느릴 수 있다고 경고함.

## 확인하지 못한 것 (로컬에서 확인 필요)

- 출력 샘플레이트 (스크립트는 모델이 돌려주는 값을 그대로 저장)
- 참조 음성 권장 길이 (스크립트는 10~20초 권장, 30초 초과 시 앞부분만 사용)
- 1.7B 모델의 VRAM 요구량. 8GB GPU에서 안 되면 0.6B 로 시도.
- 말 속도 조절 옵션 존재 여부. 대본이 빠른 말투 기준이므로 우선 기본값으로 생성하고 결과 길이를 보고 판단.
