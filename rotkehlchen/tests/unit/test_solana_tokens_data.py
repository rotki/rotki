import csv
from pathlib import Path


def test_solana_tokens_data_unique_entries() -> None:
    """Test that entries in specified columns of solana_tokens_data.csv are unique."""
    old_id_values, address_values = [], []
    with (Path(__file__).resolve().parent.parent.parent / 'data' / 'solana_tokens_data.csv').open() as csvfile:  # noqa: E501
        reader = csv.DictReader(csvfile)
        for row in reader:
            old_id_values.append(row['old_id'])
            address_values.append(row['address'])

    for column, values in [('old_id', old_id_values), ('address', address_values)]:
        duplicates, seen = [], set()
        for value in values:
            if value in seen:
                duplicates.append(value)
            else:
                seen.add(value)

        assert len(duplicates) == 0, f'Found duplicate {column}s in solana_tokens_data.csv: {duplicates}'  # noqa: E501
