"""drug_safety.db 읽기 전용 연결.

DB 파일이 없으면(예: LFS 미pull, CI 환경) None을 반환해
상위 로직이 기존 키워드 채점으로 폴백할 수 있게 한다.
"""
import os
import sqlite3


def connect(path: str) -> sqlite3.Connection | None:
    """읽기 전용 sqlite 연결을 반환. 파일이 없으면 None."""
    if not os.path.isfile(path):
        return None
    uri = f"file:{os.path.abspath(path)}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)
