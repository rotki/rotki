import csv
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


def process_solana_asset_migration(
        write_cursor: 'DBCursor',
        table_updates: list[tuple[str, str]],
) -> list[tuple]:
    """Read solana tokens CSV and update asset identifiers across specified tables.

    Returns a list of solana token data tuples
    for insertion(empty if CSV missing or for migrations that don't need it)

    FROZEN: Do not modify. Used for v48->v49 user db upgrade and v12->v13 globaldb upgrade.
    """
    dir_path = Path(__file__).resolve().parent.parent.parent
    if not (csv_file := dir_path / 'data' / 'solana_tokens_data.csv').exists():
        return []

    asset_updates, solana_tokens_data = [], []
    with csv_file.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            asset_updates.append((new_id := f'solana/token:{row["address"]}', row['old_id']))
            solana_tokens_data.append((
                new_id,
                'D',  # spl token
                row['address'],
                row['decimals'],
                None,
            ))

    if len(asset_updates) == 0:
        return []

    # Duplicate mappings that need to be applied to other tables
    duplicate_mappings = [
        ('solana/token:BLDiYcvm3CLcgZ7XUBPgz6idSAkNmWY6MBbm8Xpjpump', 'TRISIG'),
        ('solana/token:58UC31xFjDJhv1NnBF73mtxcsxN92SWjhYRzbfmvDREJ', 'HODLSOL'),
    ]
    # For unique tables, only use assets from csv file to avoid UNIQUE constraint violations.
    # For other tables, include duplicate mappings to update old identifiers.
    unique_tables = {'assets', 'common_asset_details', 'solana_tokens'}
    for table_name, column_name in table_updates:
        if table_name in unique_tables:
            updates_to_apply = asset_updates
        else:
            updates_to_apply = asset_updates + duplicate_mappings

        when_clauses, params, in_clause_params = [], [], []
        for new_id, old_id in updates_to_apply:
            when_clauses.append('WHEN ? THEN ?')
            params.extend([old_id, new_id])
            in_clause_params.append(old_id)

        # use `case` statement to avoid executing 400+ individual update queries per table
        # original `executemany` approach was causing 5+ minute migration times due to
        # repeated index lookups and transaction overhead (53.4s -> 0.9s improvement)
        case_sql = f"""
            UPDATE {table_name}
            SET {column_name} = CASE {column_name}
                {' '.join(when_clauses)}
                ELSE {column_name}
            END
            WHERE {column_name} IN ({','.join(['?'] * len(in_clause_params))})
        """
        all_params = params + in_clause_params
        write_cursor.execute(case_sql, all_params)

    return solana_tokens_data
