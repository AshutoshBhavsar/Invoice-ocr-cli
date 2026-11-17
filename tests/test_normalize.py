from datetime import date

import pytest

from invoice_ocr.normalize import (
    NormalizationError,
    normalize_invoice_number,
    normalize_vendor,
    parse_date,
    parse_money_to_paise,
)


@pytest.mark.parametrize(
    "raw, paise",
    [
        ("1200.50", 120050),
        ("1,200.50", 120050),  
        ("1500.00", 150000),
        ("1500", 150000),
        ("216.09", 21609),
        ("0.5", 50),
    ],
)
def test_money_is_converted_to_exact_paise(raw, paise):
    assert parse_money_to_paise(raw) == paise


@pytest.mark.parametrize("raw", ["11?0.00", "", "abc", "-5.00", "1.234", "12,34.00"])
def test_unreadable_money_is_rejected_not_guessed(raw):
    with pytest.raises(NormalizationError) as exc:
        parse_money_to_paise(raw)
    assert exc.value.code == "invalid_amount"


@pytest.mark.parametrize("raw", ["2026-10-01", "01/10/2026"])
def test_both_date_formats_give_the_same_date(raw):
    assert parse_date(raw) == date(2026, 10, 1)


@pytest.mark.parametrize("raw", ["[not supplied]", "", "2026-13-01", "31/02/2026"])
def test_bad_dates_are_rejected(raw):
    with pytest.raises(NormalizationError) as exc:
        parse_date(raw)
    assert exc.value.code == "invalid_date"


def test_vendor_names_that_differ_only_in_case_or_spacing_match():
    assert normalize_vendor("Acme Office Supplies") == normalize_vendor("  ACME   OFFICE SUPPLIES ")


def test_invoice_number_is_trimmed_and_upper_cased():
    assert normalize_invoice_number(" tnm-101 ") == "TNM-101"
