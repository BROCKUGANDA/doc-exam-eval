"""Normalised value types for documentary credit examination.

This module exists to make one failure class impossible: a model giving a correct
answer in a different representation and being marked wrong. Money, dates and
quantities are therefore compared only after normalisation, and the normalisation
rules come from the rulebook rather than from hard-coded assumptions.

Ambiguity is a first-class result, not an exception — an ambiguous date is *not
established*, which is what makes "know when not to decide" gradeable.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from benchmark.rulebook.model import Rulebook

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


class NotEstablished(Exception):
    """A value could not be established from the document. Never a discrepancy."""


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------
_MONEY_RE = re.compile(
    r"^\s*(?:(?P<cur_pre>[A-Z]{3})\s*)?(?P<num>-?[\d,]+(?:\.\d+)?)\s*(?:(?P<cur_post>[A-Z]{3}))?\s*$"
)


@dataclass(frozen=True)
class Money:
    currency: str
    amount: Decimal
    rendering: str = ""

    def rounded(self, minor_units: int) -> Decimal:
        q = Decimal(1).scaleb(-minor_units)
        return self.amount.quantize(q, rounding=ROUND_HALF_UP)

    def __str__(self) -> str:
        return f"{self.currency} {self.amount}"


_DIGIT_GROUP_SPACE = re.compile(r"(?<=\d) (?=\d)")


def parse_money(raw: str, *, default_currency: str | None = None) -> Money:
    """Accept any rendering the corpus can produce: 'USD 100,000.00',
    '100000 USD', 'USD 100 000'. Raises NotEstablished on garbage so a bad parse
    can never masquerade as a discrepancy."""
    if raw is None:
        raise NotEstablished("money field absent")
    text = str(raw).replace("\u00a0", " ").replace(",", "").strip()
    text = _DIGIT_GROUP_SPACE.sub("", text)
    m = _MONEY_RE.match(text)
    if not m:
        raise NotEstablished(f"money field unparseable: {raw!r}")
    currency = m.group("cur_pre") or m.group("cur_post") or default_currency
    if not currency:
        raise NotEstablished(f"money field has no currency: {raw!r}")
    try:
        amount = Decimal(m.group("num"))
    except InvalidOperation as exc:  # pragma: no cover - regex prevents this
        raise NotEstablished(f"money amount invalid: {raw!r}") from exc
    return Money(currency=currency.upper(), amount=amount, rendering=str(raw).strip())


def money_equal(a: Money, b: Money, rb: Rulebook) -> bool:
    """Equal after rounding to the currency's own minor units, per money_equality.
    Different currencies are never equal here — that is RULE-AMT-003's job."""
    if a.currency != b.currency:
        return False
    units = rb.minor_units(a.currency)
    return a.rounded(units) == b.rounded(units)


def money_within_pct(base: Money, candidate: Money, pct: Decimal, rb: Rulebook) -> bool:
    """Is candidate inside +/- pct of base, compared at minor-unit precision?"""
    if base.currency != candidate.currency:
        return False
    units = rb.minor_units(base.currency)
    if base.amount == 0:
        return candidate.rounded(units) == 0
    b, c = base.rounded(units), candidate.rounded(units)
    limit = (abs(b) * pct / Decimal(100)).quantize(Decimal(1).scaleb(-units), rounding=ROUND_HALF_UP)
    return abs(c - b) <= limit


def renders_with_minor_units(money: Money, rb: Rulebook) -> bool:
    """False when the document writes 'USD 100000' for a 2-decimal currency.
    Presentation only — value equality is decided elsewhere."""
    units = rb.minor_units(money.currency)
    text = money.rendering
    if units == 0:
        return "." not in text
    m = re.search(r"(\d+)(?:\.(\d+))?\s*$", text)
    if not m:
        return False
    decimals = m.group(2)
    return decimals is not None and len(decimals) == units


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DateResult:
    value: date | None
    ambiguous: bool
    raw: str

    @property
    def established(self) -> bool:
        return self.value is not None and not self.ambiguous


def parse_date(raw: str, rb: Rulebook | None = None) -> DateResult:
    """Parse every accepted rendering. Slash forms are resolved only when the
    corpus declares which pattern it uses; otherwise the date is ambiguous.

    The accepted-rendering list lives in the rulebook's date_formats definition for
    documentation; the parser below is the single implementation of it, so `rb` is
    optional and only present so call sites can read as rulebook-driven."""
    if raw is None:
        return DateResult(None, False, "")
    text = str(raw).strip()
    if not text:
        return DateResult(None, False, text)

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return DateResult(date(int(m[1]), int(m[2]), int(m[3])), False, text)

    m = re.fullmatch(r"(\d{4})\.(\d{2})\.(\d{2})", text)
    if m:
        return DateResult(date(int(m[1]), int(m[2]), int(m[3])), False, text)

    m = re.fullmatch(r"(\d{1,2})[.-](\w{3,})[.-](\d{4})", text, re.IGNORECASE)
    if m:
        mon = _MONTHS.get(m[2][:3].lower())
        if mon:
            return DateResult(date(int(m[3]), mon, int(m[1])), False, text)

    m = re.fullmatch(r"(\w{3,})\s+(\d{1,2}),?\s+(\d{4})", text, re.IGNORECASE)
    if m:
        mon = _MONTHS.get(m[1][:3].lower())
        if mon:
            return DateResult(date(int(m[3]), mon, int(m[2])), False, text)

    m = re.fullmatch(r"(\d{1,2})\s+(\w{3,}),?\s+(\d{4})", text, re.IGNORECASE)
    if m:
        mon = _MONTHS.get(m[2][:3].lower())
        if mon:
            return DateResult(date(int(m[3]), mon, int(m[1])), False, text)

    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if m:
        # 03/04/2025 is genuinely two different dates depending on convention.
        # Rulebook date_formats lists DD/MM and MM-DD as separate accepted
        # renderings, so an unprefixed slash date cannot be resolved.
        return DateResult(None, True, text)

    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", text)
    if m:
        return DateResult(None, True, text)

    return DateResult(None, False, text)


def iso(d: date) -> str:
    return d.isoformat()


# ---------------------------------------------------------------------------
# Quantities
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Quantity:
    value: Decimal
    unit: str
    rendering: str = ""

    def __str__(self) -> str:
        return f"{self.value} {self.unit}"


def parse_quantity(raw: str) -> Quantity:
    if raw is None:
        raise NotEstablished("quantity absent")
    text = str(raw).replace(",", "").strip().upper()
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*([A-Z]+(?:\s?[A-Z]+)?)", text)
    if not m:
        raise NotEstablished(f"quantity unparseable: {raw!r}")
    return Quantity(Decimal(m[1]), m[2].strip(), str(raw).strip())


def convert_quantity(q: Quantity, target_unit: str, rb: Rulebook) -> Decimal | None:
    """Convert only along a rulebook-sanctioned factor. None means the pair has no
    permitted conversion, which the caller must treat as not established."""
    target = target_unit.strip().upper()
    if q.unit == target:
        return q.value
    factor = rb.unit_conversion_factor(q.unit, target)
    if factor is None:
        return None
    return q.value * Decimal(str(factor))


def quantities_comparable(a: Quantity, b: Quantity, rb: Rulebook) -> bool:
    if a.unit == b.unit:
        return True
    return rb.unit_conversion_factor(a.unit, b.unit) is not None


def quantity_within_pct(base: Quantity, candidate: Quantity, pct: Decimal, rb: Rulebook) -> bool:
    """pct == 0 means exact equality after conversion, i.e. no tolerance at all."""
    if base.value == 0:
        return candidate.value == 0
    if pct == 0:
        return decimal_equal(base, candidate, rb)
    conv = convert_quantity(candidate, base.unit, rb)
    if conv is None:
        return False
    limit = base.value * pct / Decimal(100)
    return abs(conv - base.value) <= limit


def decimal_equal(a: Quantity, b: Quantity, rb: Rulebook) -> bool:
    conv = convert_quantity(b, a.unit, rb)
    if conv is None:
        return False
    return a.value == conv


# ---------------------------------------------------------------------------
# Text / citation normalisation
# ---------------------------------------------------------------------------
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")


def normalize_location(text: str) -> str:
    """Case-fold, de-accent and strip punctuation so 'Total amount',
    'TOTAL AMOUNT:' and 'total  amount' all point at the same place — while
    remaining strict enough that an invented location still fails."""
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = _PUNCT.sub(" ", s)
    return _SPACE.sub(" ", s).strip()


_ALNUM = re.compile(r"[^a-z0-9]")


def location_matches(a: str, b: str) -> bool:
    """Citation equality as the grader uses it.

    Canonical form first, then an alphanumeric-squashed form so that dotted
    abbreviations ('T.T.R. No. 44') and hyphenated labels ('port-of-loading')
    still resolve to the field they name. The squash step is only ever a
    *fallback*, which keeps genuinely different locations distinct.
    """
    ca, cb = normalize_location(a), normalize_location(b)
    if ca == cb:
        return True
    return _ALNUM.sub("", ca) == _ALNUM.sub("", cb)


def description_tokens(text: str) -> frozenset[str]:
    return frozenset(normalize_location(text).split())


@dataclass
class Evidence:
    document_id: str
    page: int
    location: str
    note: str = ""


@dataclass
class FindingValue:
    """A value observed somewhere, used in observed_values of a discrepancy."""

    label: str
    value: str
