from invoice_ocr.parser import parse_fields
from samples import TNM_101, TNM_101_COPY, TNM_102, TNM_103_REVIEW


def test_all_seven_fields_are_found():
    fields = parse_fields(TNM_101)
    assert fields.as_dict() == {
        "invoice_number": "TNM-101",
        "vendor": "Acme Office Supplies",
        "date": "2026-10-01",
        "currency": "INR",
        "subtotal": "1200.50",
        "tax": "216.09",
        "total": "1416.59",
    }


def test_values_are_returned_exactly_as_printed():
    fields = parse_fields(TNM_101_COPY)
    assert fields.vendor == "ACME OFFICE SUPPLIES"
    assert fields.date == "01/10/2026"
    assert fields.subtotal == "1,200.50"


def test_total_is_not_confused_with_subtotal():
    fields = parse_fields(TNM_102)
    assert fields.subtotal == "1500.00"
    assert fields.total == "1770.00"


def test_odd_values_pass_through_unchanged_for_later_validation():
    fields = parse_fields(TNM_103_REVIEW)
    assert fields.date == "[not supplied]"
    assert fields.total == "1120.00"


def test_missing_label_gives_none():
    fields = parse_fields("Invoice: TNM-9\nVendor: Foo\n")
    assert fields.invoice_number == "TNM-9"
    assert fields.total is None
    assert fields.date is None


def test_empty_value_gives_none():
    assert parse_fields("Vendor:   \n").vendor is None
