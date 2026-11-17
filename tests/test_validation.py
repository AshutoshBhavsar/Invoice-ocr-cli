from datetime import date

from invoice_ocr.parser import RawInvoiceFields, parse_fields
from invoice_ocr.validation import NEEDS_REVIEW, VALID, validate

from samples import TNM_101, TNM_101_COPY, TNM_102, TNM_103_REVIEW


def _valid_raw(**overrides) -> RawInvoiceFields:
    base = dict(
        invoice_number="TNM-9",
        vendor="Foo Ltd",
        date="2026-10-01",
        currency="INR",
        subtotal="100.00",
        tax="18.00",
        total="118.00",
    )
    base.update(overrides)
    return RawInvoiceFields(**base)


def test_valid_invoice_has_clean_values_and_no_reasons():
    result = validate(parse_fields(TNM_101))

    assert result.status == VALID
    assert result.reasons == ()
    inv = result.invoice
    assert inv.invoice_number == "TNM-101"
    assert inv.vendor_key == "acme office supplies"
    assert inv.invoice_date == date(2026, 10, 1)
    assert inv.currency == "INR"
    assert (inv.subtotal_paise, inv.tax_paise, inv.total_paise) == (120050, 21609, 141659)


def test_second_valid_invoice_passes():
    assert validate(parse_fields(TNM_102)).is_valid


def test_rescanned_copy_validates_to_the_same_values_and_key():
    original = validate(parse_fields(TNM_101)).invoice
    copy_result = validate(parse_fields(TNM_101_COPY))
    copy = copy_result.invoice

    assert copy_result.is_valid
    assert (copy.invoice_number, copy.vendor_key) == (original.invoice_number, original.vendor_key)
    assert copy.invoice_date == original.invoice_date
    assert copy.total_paise == original.total_paise


def test_incomplete_ambiguous_invoice_needs_review_with_both_reasons():
    result = validate(parse_fields(TNM_103_REVIEW))

    assert result.status == NEEDS_REVIEW
    assert sorted(result.reason_codes) == ["invalid_date", "total_mismatch"]
    # what was read correctly is still kept, nothing is discarded
    assert result.invoice.invoice_number == "TNM-103"
    assert result.invoice.total_paise == 112000
    assert result.invoice.invoice_date is None


def test_total_mismatch_message_shows_the_numbers():
    result = validate(parse_fields(TNM_103_REVIEW))
    message = next(r.message for r in result.reasons if r.code == "total_mismatch")
    assert "1180.00" in message and "1120.00" in message


def test_every_missing_field_is_reported():
    result = validate(parse_fields("Invoice: TNM-9\n"))
    assert set(result.reason_codes) == {
        "missing_vendor",
        "missing_date",
        "missing_currency",
        "missing_subtotal",
        "missing_tax",
        "missing_total",
    }


def test_unreadable_amount_is_reported_and_sum_is_not_checked():
    result = validate(_valid_raw(total="11?0.00"))
    assert result.reason_codes == ["invalid_amount"]  # no misleading total_mismatch
    assert result.invoice.total_paise is None


def test_only_the_sum_is_wrong():
    result = validate(_valid_raw(total="120.00"))
    assert result.reason_codes == ["total_mismatch"]


def test_bad_currency_needs_review():
    assert validate(_valid_raw(currency="R$")).reason_codes == ["invalid_currency"]


def test_currency_is_upper_cased():
    assert validate(_valid_raw(currency=" inr ")).invoice.currency == "INR"
