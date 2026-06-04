import sqlite3

import pytest

from app.agentic_ai.drug_db.connection import connect


def _make_db(path) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE t (x TEXT)")
    con.execute("INSERT INTO t VALUES ('hi')")
    con.commit()
    con.close()


def test_connect_returns_none_when_db_missing(tmp_path):
    assert connect(str(tmp_path / "nope.db")) is None


def test_connect_opens_existing_db(tmp_path):
    db_path = tmp_path / "tiny.db"
    _make_db(db_path)

    conn = connect(str(db_path))
    assert conn is not None
    assert conn.execute("SELECT x FROM t").fetchone()[0] == "hi"


def test_connect_is_read_only(tmp_path):
    db_path = tmp_path / "tiny.db"
    _make_db(db_path)

    conn = connect(str(db_path))
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO t VALUES ('nope')")
