import pytest

import database


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "users.db"))
    database.init_db()


def test_upsert_creates_then_updates():
    database.upsert_user(1, first_name="هادی", phone_number="+905551112233")
    database.upsert_user(1, national_id="1234567891", kyc_status="Approved")
    user = database.get_user(1)
    assert user["first_name"] == "هادی"
    assert user["national_id"] == "1234567891"
    assert user["kyc_status"] == "Approved"
    assert database.get_user_by_phone("+905551112233")["id"] == 1


def test_unknown_columns_are_rejected():
    with pytest.raises(ValueError):
        database.upsert_user(1, **{"id=1; DROP TABLE users; --": "x"})


def test_set_user_docs():
    database.set_user_docs(2, front_id="front-file", back_id="back-file")
    user = database.get_user(2)
    assert (user["front_id"], user["back_id"]) == ("front-file", "back-file")
