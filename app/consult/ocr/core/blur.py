"""이미지 선명도(흔들림) 평가 — 라플라시안 분산.

손떨림/초점흐림이 있으면 엣지가 약해져 라플라시안(2차 미분) 결과의 분산이 낮아진다.
값↓ = 흔들림 의심. 절대 임계값은 해상도·조명에 민감하므로 OCRConfig 에서 보정한다.
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def laplacian_variance(image_bytes: bytes) -> float | None:
    """이미지 바이트 → 라플라시안 분산. 디코딩 실패 시 None."""
    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            logger.warning("[blur] 이미지 디코딩 실패 — 선명도 측정 건너뜀")
            return None
        return float(cv2.Laplacian(img, cv2.CV_64F).var())
    except Exception as exc:  # noqa: BLE001 — 측정 실패가 OCR 전체를 막지 않도록
        logger.warning("[blur] 선명도 측정 오류: %s", exc)
        return None
