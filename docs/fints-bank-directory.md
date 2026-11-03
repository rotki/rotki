# FinTS bank directory maintenance

The bundled catalog is generated from the bank list supplied to rotki as a registered FinTS
product. It contains only the fields needed for local connection setup: institution name, city,
BLZ, and HTTPS PIN/TAN endpoint. Do not commit the registry ZIP, CSV, XLSX, history PDF, BICs, or
security-method columns.

Generate an update from the ZIP supplied by the registry:

```bash
uv run python tools/scripts/generate_fints_bank_directory.py \
  /path/to/fints_institute.zip \
  frontend/app/src/modules/banks/fints-bank-directory.json \
  --version YYYY-MM-DD
```

The JSON uses a compact generated format:

- `v`: registry version date.
- `h`: SHA-256 of the input ZIP, so an update can be reproduced and audited.
- `e`: deduplicated endpoint table.
- `b`: institution tuples containing name, city, endpoint-table index, BLZ or BLZ array, and an
  optional aliases array.
- `g`: logo file name to the indices in `b` of the institutions shown with it. The files live in
  `frontend/app/public/assets/images/protocols`. An institution with no logo keeps the generic
  bank icon.

The generator rejects non-HTTPS endpoints, embedded URL credentials, malformed BLZs, and
contradictory endpoints for one BLZ. Rows that only repeat a BLZ for branch locations are collapsed.
Institutions with the same name, city, and endpoint are grouped, while all their BLZs remain
searchable and are offered to the user when the bank requires a choice.

Logos are assigned by `NAMED_LOGOS` and `GROUP_LOGOS` in the generator. A named logo matches the
institution name. A group logo (Sparkasse, Volksbanken Raiffeisenbanken) also needs the registry's
`Organisation` column to name the association, so that a private bank with a cooperative or
savings-bank word in its name, or a foreign Sparkasse, keeps the generic icon. The logo files are
public-domain logos from Wikimedia Commons, cropped to the brand's symbol so they read at icon size.
To add a bank, add its cropped logo file and a `NAMED_LOGOS` entry, then regenerate.

The catalog is connection metadata, not a support guarantee. Keep the manual FinTS/HBCI option in
the bank selector so an unlisted institution or an emergency endpoint correction never blocks setup.
