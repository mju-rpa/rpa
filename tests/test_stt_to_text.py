from app.consult.stt.api.schema.schema import SpeakerSegment, TranscribeResponse
from app.consult.stt.service import to_text


def test_to_text_joins_speaker_segments():
    data = TranscribeResponse(
        text="전체 텍스트",
        language="ko",
        duration=5.0,
        segments=[
            SpeakerSegment(speaker="A", text="안녕하세요", start=0.0, end=1.0),
            SpeakerSegment(speaker="B", text="네 반갑습니다", start=1.0, end=2.0),
        ],
    )

    assert to_text(data) == "A: 안녕하세요\nB: 네 반갑습니다"


def test_to_text_falls_back_to_plain_text_without_segments():
    data = TranscribeResponse(text="화자 분리 없는 텍스트", language="ko", duration=5.0, segments=[])

    assert to_text(data) == "화자 분리 없는 텍스트"
