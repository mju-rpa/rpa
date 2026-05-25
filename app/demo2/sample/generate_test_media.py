"""
Demo2용 임시 샘플 생성 (팀 실데이터 없을 때).

  python app/demo2/sample/generate_test_media.py

필요: pip install pillow
선택(한국어 음성): pip install gtts
  gtts 사용 시 mp3 생성 후 표준 library wave 로는 mp3 미지원 →
  ffmpeg 있으면: ffmpeg -i visit.mp3 visit.wav
"""
from __future__ import annotations

import struct
import wave
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_PILL = _DIR / "pill.jpg"
_VISIT_WAV = _DIR / "visit.wav"
_VISIT_MP3 = _DIR / "visit.mp3"

# OCR 테스트용 한글 (가상 처방)
_PILL_TEXT = """
[교육용 모의 약봉투]
환자명: 김철수
처방일: 2026-05-20
병원: OO약국

1. 넥시움정 (위산억제제) — 1일 1회, 식전 30분, 7일분
2. 타이레놀정 (진통제) — 증상 시 1정, 최대 1일 3회

※ 우유와 함께 복용하지 마세요.
"""

_STT_SCRIPT = (
    "의사: 최근에 속 쓰림은 어떠신가요? "
    "환자: 밥 먹고 나면 신물이 올라와요. "
    "의사: 위산 억제제는 아침 식전에 드시고, "
    "진통제는 두통할 때만 드세요. "
    "우유와 같이 드시면 안 됩니다."
)


def generate_pill_jpg() -> Path:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise SystemExit("pill.jpg 생성에 Pillow 필요: pip install pillow") from e

    img = Image.new("RGB", (720, 900), color=(255, 255, 240))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("malgun.ttf", 22)
    except OSError:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 22)
        except OSError:
            font = ImageFont.load_default()

    y = 24
    for line in _PILL_TEXT.strip().split("\n"):
        draw.text((24, y), line.strip(), fill=(0, 0, 0), font=font)
        y += 32

    img.save(_PILL, format="JPEG", quality=92)
    print(f"[ok] {_PILL} ({_PILL.stat().st_size} bytes)")
    return _PILL


def generate_visit_gtts_mp3() -> Path | None:
    try:
        from gtts import gTTS
    except ImportError:
        print("[skip] gTTS 없음 — pip install gtts 후 재실행하면 visit.mp3 생성")
        return None

    tts = gTTS(_STT_SCRIPT, lang="ko")
    tts.save(str(_VISIT_MP3))
    print(f"[ok] {_VISIT_MP3} - convert: ffmpeg -y -i {_VISIT_MP3.name} {_VISIT_WAV.name}")
    return _VISIT_MP3


def generate_visit_silent_wav(seconds: float = 2.0, rate: int = 16000) -> Path:
    """STT API 연결만 확인할 때用的 placeholder (전사 품질 없음)."""
    n = int(rate * seconds)
    with wave.open(str(_VISIT_WAV), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{n}h", *([0] * n)))
    print(f"[ok] {_VISIT_WAV} (silent placeholder — 실제 진료 녹음으로 교체 권장)")
    return _VISIT_WAV


def main() -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    generate_pill_jpg()
    mp3 = generate_visit_gtts_mp3()
    if mp3 and _VISIT_WAV.exists():
        return
    if not _VISIT_WAV.exists():
        if mp3:
            import shutil
            import subprocess

            if shutil.which("ffmpeg"):
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(_VISIT_MP3), str(_VISIT_WAV)],
                    check=True,
                    capture_output=True,
                )
                print(f"[ok] {_VISIT_WAV} (from mp3)")
                return
        generate_visit_silent_wav()


if __name__ == "__main__":
    main()
