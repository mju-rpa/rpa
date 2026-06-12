"""drug_db 테스트용 소형 픽스처 DB.

실제 drug_safety.db(238MB, LFS)에 의존하지 않도록 동일 스키마의
축소판을 임시 파일로 만들어 결정론적으로 테스트한다.
"""
import sqlite3

import pytest


@pytest.fixture
def drug_db_path(tmp_path):
    path = tmp_path / "drug_safety.db"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE dose_limits (
            제품명 TEXT, 성분명 TEXT, 일최대투여기준량_mg REAL
        );
        CREATE TABLE duration_limits (
            제품명 TEXT, 성분명 TEXT, 최대투여기간일수 INTEGER
        );
        CREATE TABLE drug_interactions (
            성분명1 TEXT, 성분명2 TEXT, 제품명1 TEXT, 제품명2 TEXT, 금기사유 TEXT
        );
        """
    )
    con.executemany(
        "INSERT INTO dose_limits VALUES (?,?,?)",
        [
            ("타이레놀정500밀리그람(아세트아미노펜)", "acetaminophen", 4000.0),
            ("제클라정(클래리트로마이신)_(0.25g/1정)", "clarithromycin", 1000.0),
            ("심바로드정20밀리그람(심바스타틴)", "simvastatin", 80.0),
        ],
    )
    con.executemany(
        "INSERT INTO duration_limits VALUES (?,?,?)",
        [("리스카펜정_(1정)", "acetaminophen", 28)],
    )
    con.executemany(
        "INSERT INTO drug_interactions VALUES (?,?,?,?,?)",
        [
            (
                "clarithromycin",
                "simvastatin",
                "제클라정(클래리트로마이신)_(0.25g/1정)",
                "심바로드정20밀리그람(심바스타틴)",
                "근병증, 횡문근융해의 위험증가",
            ),
            # dose_limits/duration_limits 에는 없고 interactions 에만 존재하는 약
            (
                "warfarin",
                "aspirin",
                "와파린정5밀리그람(와파린나트륨)",
                "아스피린장용정100밀리그람(아스피린)",
                "출혈 위험 증가",
            ),
        ],
    )
    con.commit()
    con.close()
    return str(path)
