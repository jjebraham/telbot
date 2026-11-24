import pytest

from utils.validators import (
    is_persian_name,
    is_valid_card,
    is_valid_national_id,
    normalize_digits,
    parse_jalali_yyyymmdd,
)


def test_normalize_digits_handles_persian_and_arabic():
    assert normalize_digits("۱۲۳٤٥٦") == "123456"


@pytest.mark.parametrize("nid", ["1234567891", "0076543218", "۱۲۳۴۵۶۷۸۹۱"])
def test_valid_national_ids(nid):
    assert is_valid_national_id(nid)


@pytest.mark.parametrize("nid", ["1234567890", "1111111111", "12345", "abcdefghij"])
def test_invalid_national_ids(nid):
    assert not is_valid_national_id(nid)


def test_card_luhn_check():
    assert is_valid_card("4111 1111 1111 1111")
    assert not is_valid_card("4111 1111 1111 1112")
    assert not is_valid_card("4111")


def test_persian_name():
    assert is_persian_name("هادی")
    assert not is_persian_name("Hadi")
    assert not is_persian_name("ه")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1365 06 26", "13650626"),
        ("26/06/1365", "13650626"),
        ("۱۳۶۵-۶-۲۶", "13650626"),
        ("13650626", "13650626"),
        ("1365-13-01", None),
        ("2024-01-01", None),
        ("hello", None),
    ],
)
def test_parse_jalali(text, expected):
    assert parse_jalali_yyyymmdd(text) == expected


def test_ehraz_mock_mode(monkeypatch):
    import asyncio

    import services.ehraz as ehraz

    monkeypatch.setattr(ehraz, "EHRAZ_MOCK", True)
    assert asyncio.run(ehraz.match_card_national_dob("4111111111111111", "1234567891", "13650626"))
