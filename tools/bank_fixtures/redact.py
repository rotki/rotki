"""Redact raw bank API responses into committable test fixtures.

Framework-level tool for every bank connector. Given a directory of raw JSON
dumps (real financial data, never committed) it writes pseudonymized copies
that keep the schema, enum values, booleans, timestamps and small integers,
and replaces everything else with fakes of the same shape:

- UUIDs become stable fake UUIDs (the same real UUID always maps to the same
  fake one within a run, so cross references between files survive)
- IBANs become checksum-valid fake IBANs of the same country and length
- BICs, emails, phone numbers, URLs and postal addresses become schema-valid
  fakes
- free-form strings (names, labels, references, notes) become fake words of
  the same lengths
- monetary amounts are scaled by one random factor in [0.5, 2.0] chosen per
  run; a bank profile can then recompute derived balances so that the
  fixture stays internally consistent

The mapping is keyed by a random per-run salt that is never persisted. After
writing, a verification pass asserts that no raw leaf value (and no word of
four or more letters from any raw free-form string) survives in the output,
and fails loudly otherwise.

Usage::

    python -m tools.bank_fixtures.redact --profile qonto \
        --input .bank_spike_data/qonto --output rotkehlchen/tests/data/banks/qonto \
        organization.json transactions_acct0_page001.json
"""
import argparse
import json
import random
import re
import secrets
import string
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable

TIMESTAMP_RE: Final = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?Z?)?$')
UUID_RE: Final = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    re.IGNORECASE,
)
IBAN_RE: Final = re.compile(r'^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$')
BIC_RE: Final = re.compile(r'^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$')
EMAIL_RE: Final = re.compile(r'^[^@\s]+@[^@\s]+\.[a-z]{2,}$', re.IGNORECASE)
PHONE_RE: Final = re.compile(r'^\+?[\d\s().-]{6,}$')
URL_RE: Final = re.compile(r'^https?://', re.IGNORECASE)
ENUM_VALUE_RE: Final = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')
WORD_RE: Final = re.compile(r'[^\W\d_]{4,}', re.UNICODE)
SMALL_INT_LIMIT: Final = 1000
# Structural words that legitimately appear in both raw and redacted data
STRUCTURAL_WORDS: Final = frozenset({
    'transaction', 'bank', 'account', 'https', 'http', 'true', 'false', 'null', 'qonto',
})
FAKE_WORDS: Final = (
    'alder', 'birch', 'cedar', 'delta', 'ember', 'fjord', 'grove', 'harbor', 'ivory',
    'juniper', 'kestrel', 'lumen', 'meadow', 'nimbus', 'orchid', 'pebble', 'quartz',
    'ridge', 'saffron', 'timber', 'umber', 'velvet', 'willow', 'xenon', 'yarrow', 'zephyr',
)


class Redactor:

    def __init__(self, profile: BankProfile, amount_factor: float) -> None:
        self.profile = profile
        self.amount_factor = amount_factor
        self.salt = secrets.token_bytes(32)
        self.string_map: dict[str, str] = {}  # raw token -> fake token, for composite strings
        self.raw_leaves: set[str] = set()  # for the verification pass
        self.raw_words: set[str] = set()
        self.allowed_words: set[str] = set()  # words of preserved enum values, e.g. a legal form
        self.notes: list[str] = []

    # -- deterministic helpers ------------------------------------------------

    def _rng(self, raw: str) -> random.Random:
        return random.Random(self.salt + raw.encode())  # not cryptographic; salt is secret and per-run  # noqa: E501

    def fake_uuid(self, raw: str) -> str:
        return str(uuid.UUID(bytes=self._rng(raw).randbytes(16), version=4))

    def fake_iban(self, raw: str) -> str:
        """Same country code and length as the raw IBAN, valid mod-97 checksum."""
        rng = self._rng(raw)
        country = raw[:2]
        bban = ''.join(rng.choice(string.digits) for _ in range(len(raw) - 4))
        # ISO 7064 mod 97-10: rearranged = bban + country + '00', letters -> numbers
        rearranged = bban + country + '00'
        numeric = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
        check = 98 - int(numeric) % 97
        return f'{country}{check:02d}{bban}'

    def fake_bic(self, raw: str) -> str:
        rng = self._rng(raw)
        letters = string.ascii_uppercase
        return ''.join(rng.choice(letters) for _ in range(6)) + raw[6:8].upper() + (
            ''.join(rng.choice(letters + string.digits) for _ in range(3)) if len(raw) == 11 else ''  # noqa: E501
        )

    def fake_words(self, raw: str) -> str:
        """Replace every alphabetic run with a fake word of the same length and case shape,
        every digit run with fresh digits, and keep punctuation/whitespace."""
        rng = self._rng(raw)

        def replace_alpha(match: re.Match) -> str:
            word = match.group(0)
            fake = rng.choice(FAKE_WORDS)
            while len(fake) < len(word):
                fake += rng.choice(FAKE_WORDS)
            fake = fake[:len(word)]
            if word.isupper():
                return fake.upper()
            if word[0].isupper():
                return fake.capitalize()
            return fake

        result = re.sub(r'[^\W\d_]+', replace_alpha, raw)
        return re.sub(r'\d+', lambda m: ''.join(rng.choice(string.digits) for _ in m.group(0)), result)  # noqa: E501

    def fake_email(self, raw: str) -> str:
        rng = self._rng(raw)
        return f'{rng.choice(FAKE_WORDS)}.{rng.choice(FAKE_WORDS)}@example.com'

    def fake_phone(self, raw: str) -> str:
        rng = self._rng(raw)
        return '+49 30 ' + ''.join(rng.choice(string.digits) for _ in range(7))

    def fake_url(self, raw: str) -> str:
        rng = self._rng(raw)
        suffix = raw.rsplit('.', 1)[-1] if '.' in raw.rsplit('/', 1)[-1] else 'png'
        return f'https://example.com/{rng.choice(FAKE_WORDS)}/{self.fake_uuid(raw)}.{suffix[:4]}'

    # -- walking --------------------------------------------------------------

    def collect_tokens(self, value: Any, key: str = '') -> None:
        """First pass: learn the tokens (uuids, slugs, ibans, bics) that may be embedded
        inside other strings, so that composite strings can be rewritten consistently."""
        if isinstance(value, dict):
            for k, v in value.items():
                self.collect_tokens(v, k)
        elif isinstance(value, list):
            for item in value:
                self.collect_tokens(item, key)
        elif isinstance(value, str):
            for match in UUID_RE.findall(value):
                self.string_map.setdefault(match, self.fake_uuid(match))
            if key in self.profile.token_keys and value:
                if IBAN_RE.match(value):
                    self.string_map.setdefault(value, self.fake_iban(value))
                elif BIC_RE.match(value):
                    self.string_map.setdefault(value, self.fake_bic(value))
                else:
                    self.string_map.setdefault(value, self.fake_words(value))

    def redact(self, value: Any, key: str = '') -> Any:
        if isinstance(value, dict):
            return {k: self.redact(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(item, key) for item in value]
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, int | float):
            return self._redact_number(value, key)
        if isinstance(value, str):
            return self._redact_string(value, key)
        raise TypeError(f'unexpected json value type {type(value)}')

    def _redact_number(self, value: float, key: str) -> float:
        if key in self.profile.amount_keys or any(part in key for part in self.profile.amount_key_parts):  # noqa: E501
            self.raw_leaves.add(str(value))
            scaled = value * self.amount_factor
            return round(scaled) if isinstance(value, int) else round(scaled, 2)
        if isinstance(value, int) and abs(value) < SMALL_INT_LIMIT:
            return value
        if key in self.profile.preserved_keys:
            return value
        self.raw_leaves.add(str(value))
        return round(value * self.amount_factor, 2) if isinstance(value, float) else int(value * self.amount_factor)  # noqa: E501

    def _redact_string(self, value: str, key: str) -> str:
        if (
                value == '' or
                key in self.profile.preserved_keys or
                value in self.profile.preserved_values or
                TIMESTAMP_RE.match(value) or
                (key in self.profile.enum_keys and ENUM_VALUE_RE.match(value))
        ):
            self.allowed_words.update(w.lower() for w in WORD_RE.findall(value))
            return value
        self.raw_leaves.add(value)
        # composite strings: swap every known token, longest first
        rewritten = value
        for raw_token in sorted(self.string_map, key=len, reverse=True):
            if raw_token in rewritten:
                rewritten = rewritten.replace(raw_token, self.string_map[raw_token])
        if rewritten != value:
            for word in WORD_RE.findall(value):
                if word.lower() not in STRUCTURAL_WORDS and word in rewritten:
                    self.notes.append(f'{key}: word {word!r} survived token swap; faking whole string')  # noqa: E501
                    return self.fake_words(value)
            return rewritten
        self.raw_words.update(w.lower() for w in WORD_RE.findall(value))
        if IBAN_RE.match(value):
            return self.fake_iban(value)
        if BIC_RE.match(value):
            return self.fake_bic(value)
        if EMAIL_RE.match(value):
            return self.fake_email(value)
        if URL_RE.match(value):
            return self.fake_url(value)
        if PHONE_RE.match(value) and any(c.isdigit() for c in value):
            return self.fake_phone(value)
        return self.fake_words(value)

    # -- verification ---------------------------------------------------------

    def verify(self, redacted: list[Any]) -> list[str]:
        """Return the list of raw values that leaked into the redacted output.

        Only output leaf values are inspected, dict keys are schema and never redacted.
        Numbers must match as whole tokens, strings as substrings.
        """
        leaves: list[str] = []
        _collect_leaves(redacted, leaves)
        lowered = '\n'.join(leaves).lower()
        leaks = []
        for leaf in self.raw_leaves:
            if len(leaf) < 4:
                continue
            if _is_number(leaf):
                if re.search(rf'(?<![\d.]){re.escape(leaf)}(?![\d.])', lowered):
                    leaks.append(f'value {leaf!r}')
            elif leaf.lower() in lowered:
                leaks.append(f'value {leaf!r}')
        allowed = STRUCTURAL_WORDS | set(FAKE_WORDS) | self.allowed_words
        leaks.extend(
            f'word {word!r}' for word in self.raw_words
            if word not in allowed and word in lowered
        )
        return leaks


def _collect_leaves(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        for v in value.values():
            _collect_leaves(v, out)
    elif isinstance(value, list):
        for item in value:
            _collect_leaves(item, out)
    elif value is not None and not isinstance(value, bool):
        out.append(str(value))


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class BankProfile:
    """Per-bank knowledge: which keys hold what. Keep these declarative."""
    name: str
    token_keys: frozenset[str]
    enum_keys: frozenset[str]
    preserved_keys: frozenset[str]
    amount_keys: frozenset[str]
    amount_key_parts: tuple[str, ...]
    preserved_values: frozenset[str] = frozenset()  # e.g. the bank's own name as a label
    post_process: Callable[[dict[str, Any]], None] | None = None


def _qonto_recompute_balances(body: dict[str, Any]) -> None:
    """Scaled amounts break the running `settled_balance`; recompute it in settled order and
    push the final balance onto the account object when both live in the same file."""
    transactions = body.get('transactions')
    if not isinstance(transactions, list):
        return
    running: dict[str, int] = {}
    for tx in sorted(transactions, key=lambda t: t.get('settled_at') or ''):
        if tx.get('settled_at') is None or tx.get('settled_balance_cents') is None:
            continue
        signed = tx['amount_cents'] if tx.get('side') == 'credit' else -tx['amount_cents']
        balance = running.get(tx['bank_account_id'], 0) + signed
        running[tx['bank_account_id']] = balance
        tx['settled_balance_cents'] = balance
        tx['settled_balance'] = balance / 100
    for tx in transactions:  # keep float and cents columns consistent after scaling
        for cents_key in ('amount_cents', 'local_amount_cents', 'vat_amount_cents'):
            if isinstance(tx.get(cents_key), int):
                tx[cents_key.removesuffix('_cents')] = tx[cents_key] / 100


PROFILES: Final = {
    'qonto': BankProfile(
        name='qonto',
        token_keys=frozenset({
            'slug', 'iban', 'bic', 'legal_number', 'account_number',
            'counterparty_account_number', 'counterparty_bank_identifier',
        }),
        enum_keys=frozenset({
            'status', 'side', 'operation_type', 'currency', 'local_currency', 'category',
            'subject_type', 'legal_form', 'legal_country', 'locale', 'legal_sector',
            'counterparty_account_number_format', 'counterparty_bank_identifier_format',
            'file_content_type', 'transfer_type', 'kind', 'type',
        }),
        preserved_keys=frozenset({
            'total_pages', 'total_count', 'current_page', 'next_page', 'prev_page', 'per_page',
            'vat_rate', 'file_size', 'card_last_digits',
        }),
        amount_keys=frozenset({'legal_share_capital'}),
        amount_key_parts=('amount', 'balance'),
        preserved_values=frozenset({'Qonto'}),
        post_process=_qonto_recompute_balances,
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)  # noqa: E501
    parser.add_argument('--profile', required=True, choices=sorted(PROFILES))
    parser.add_argument('--input', required=True, type=Path, help='directory with raw dumps')
    parser.add_argument('--output', required=True, type=Path, help='directory for fixtures')
    parser.add_argument('files', nargs='+', help='raw file names (relative to --input)')
    parser.add_argument('--body-key', default='body', help='key holding the API body in raw dumps, or "" if the dump is the body itself')  # noqa: E501
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    redactor = Redactor(profile=profile, amount_factor=random.uniform(0.5, 2.0))
    raw_bodies: dict[str, Any] = {}
    for name in args.files:
        raw = json.loads((args.input / name).read_text(encoding='utf8'))
        raw_bodies[name] = raw[args.body_key] if args.body_key else raw
        redactor.collect_tokens(raw_bodies[name])

    args.output.mkdir(parents=True, exist_ok=True)
    written: list[tuple[Path, Any]] = []
    for name, body in raw_bodies.items():
        redacted = redactor.redact(body)
        if profile.post_process is not None and isinstance(redacted, dict):
            profile.post_process(redacted)
        written.append((args.output / name, redacted))

    leaks = redactor.verify([redacted for _, redacted in written])
    if leaks:
        print('REDACTION FAILED, raw data would leak:', file=sys.stderr)
        for leak in leaks:
            print(f'  {leak}', file=sys.stderr)
        sys.exit(1)

    for path, redacted in written:
        path.write_text(json.dumps(redacted, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
        print(f'wrote {path}')
    for note in redactor.notes:
        print(f'note: {note}')
    print(f'verified: {len(redactor.raw_leaves)} raw leaf values and {len(redactor.raw_words)} raw words absent from output')  # noqa: E501


if __name__ == '__main__':
    main()
