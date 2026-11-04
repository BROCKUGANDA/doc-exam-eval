"""Unit tests for the normalisation layer.

Every assertion here is a false-fail that would otherwise be silently inflicted on
a model that answered correctly in a different representation.
"""

from datetime import date
from decimal import Decimal

import pytest

from benchmark.domain import (
    NotEstablished,
    convert_quantity,
    decimal_equal,
    money_equal,
    money_within_pct,
    location_matches,
    normalize_location,
    parse_date,
    parse_money,
    parse_quantity,
    quantity_within_pct,
    renders_with_minor_units,
)
from benchmark.rulebook import rulebook

RB = rulebook()


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "a,b",
    [
        ("USD 100,000.00", "USD 100000"),
        ("USD 100,000.00", "USD 100000.0"),
        ("USD 100,000.00", "100000.00 USD"),
        ("USD 100 000.00", "USD 100000.00"),
        ("EUR 1,234.56", "EUR 1234.560"),
    ],
)
def test_equivalent_renderings_are_equal(a, b):
    assert money_equal(parse_money(a), parse_money(b), RB)


def test_the_guides_own_rounding_trap_is_not_a_discrepancy():
    """Participant Guide p.10: 96.12 must not be marked wrong because the true
    value is 96.124991."""
    assert money_equal(parse_money("USD 96.12"), parse_money("USD 96.124991"), RB)


def test_a_real_cent_difference_is_a_difference():
    assert not money_equal(parse_money("USD 96.12"), parse_money("USD 96.13"), RB)


def test_zero_decimal_currency_uses_its_own_precision():
    assert money_equal(parse_money("JPY 1000000"), parse_money("JPY 1000000.4"), RB)
    assert not money_equal(parse_money("JPY 1000000"), parse_money("JPY 1000000.5"), RB)


def test_different_currencies_are_never_equal_at_this_layer():
    assert not money_equal(parse_money("USD 1000.00"), parse_money("EUR 1000.00"), RB)


def test_money_with_no_currency_and_no_default_is_not_established():
    with pytest.raises(NotEstablished):
        parse_money("1000.00")
    assert parse_money("1000.00", default_currency="USD").currency == "USD"


def test_garbage_is_not_established_rather_than_zero():
    for bad in ("USD twelve", "", None, "USD 1.2.3"):
        with pytest.raises(NotEstablished):
            parse_money(bad)


def test_tolerance_band_boundaries_are_inclusive():
    base = parse_money("USD 100,000.00")
    assert money_within_pct(base, parse_money("USD 110,000.00"), Decimal(10), RB)
    assert money_within_pct(base, parse_money("USD 90,000.00"), Decimal(10), RB)
    assert not money_within_pct(base, parse_money("USD 110,000.01"), Decimal(10), RB)


def test_zero_baseline_does_not_divide_by_zero():
    assert money_within_pct(parse_money("USD 0.00"), parse_money("USD 0.00"), Decimal(5), RB)
    assert not money_within_pct(parse_money("USD 0.00"), parse_money("USD 0.01"), Decimal(5), RB)


def test_presentation_defect_is_about_rendering_not_value():
    assert renders_with_minor_units(parse_money("USD 100,000.00"), RB)
    assert not renders_with_minor_units(parse_money("USD 100000"), RB)
    assert renders_with_minor_units(parse_money("JPY 1000000"), RB)


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw",
    ["2026-03-05", "5 March 2026", "Mar 5 2026", "05-Mar-2026", "March 5, 2026", "2026.03.05"],
)
def test_accepted_formats_resolve_to_the_same_calendar_date(raw):
    res = parse_date(raw, RB)
    assert res.established, raw
    assert res.value == date(2026, 3, 5)


def test_ambiguous_numeric_date_is_not_established_but_is_ambiguous():
    res = parse_date("03/04/2025", RB)
    assert not res.established
    assert res.ambiguous is True


def test_unparseable_date_is_not_established_and_not_ambiguous():
    res = parse_date("soon", RB)
    assert not res.established
    assert res.ambiguous is False


# ---------------------------------------------------------------------------
# Quantities
# ---------------------------------------------------------------------------
def test_permitted_conversion_makes_different_units_equal():
    mt = parse_quantity("12.5 MT")
    kg = parse_quantity("12500 KG")
    assert decimal_equal(mt, kg, RB)
    assert convert_quantity(mt, "KG", RB) == Decimal("12500")


def test_carton_to_piece_has_no_default_factor():
    """Guessing a factor would invent a discrepancy, so conversion must refuse."""
    assert convert_quantity(parse_quantity("40 CTN"), "PCS", RB) is None
    assert not quantity_within_pct(parse_quantity("1000 PCS"), parse_quantity("40 CTN"), Decimal(5), RB)


def test_packaged_goods_have_no_tolerance():
    base = parse_quantity("1,000 PCS".replace(",", ""))
    assert quantity_within_pct(base, parse_quantity("1000 PCS"), Decimal(0), RB)
    assert not quantity_within_pct(base, parse_quantity("999 PCS"), Decimal(0), RB)


def test_bulk_tolerance_is_five_percent_inclusive():
    base = parse_quantity("1000 MT")
    assert quantity_within_pct(base, parse_quantity("950 MT"), Decimal(5), RB)
    assert not quantity_within_pct(base, parse_quantity("949 MT"), Decimal(5), RB)


def test_cross_unit_tolerance_check_uses_converted_values():
    base = parse_quantity("1000 MT")
    assert quantity_within_pct(base, parse_quantity("980000 KG"), Decimal(5), RB)


# ---------------------------------------------------------------------------
# Citation normalisation
# ---------------------------------------------------------------------------
def test_locations_normalise_across_punctuation_and_case():
    assert normalize_location("Total amount:") == normalize_location("total  AMOUNT")
    assert normalize_location("Port of Loading") == normalize_location("port of loading")


def test_citation_matching_tolerates_abbreviations_and_hyphenation():
    assert location_matches("T.T.R. No. 44", "TTR No 44")
    assert location_matches("port-of-loading", "Port of loading")
    assert location_matches("TOTAL AMOUNT", "Total amount")


def test_citation_matching_still_rejects_a_different_field():
    """The whole point of the strictness: an invented location must not match."""
    assert not location_matches("Total amount", "Quantity of goods")
    assert not location_matches("Port of loading", "Port of discharge")
    assert not location_matches("Issue date", "Valid until")


def test_a_wrong_location_still_differs():
    assert normalize_location("Total amount") != normalize_location("Quantity of goods")
