import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

/**
 * Snapshot CSV shape mirrors the backend's `_for_import` serializer in
 * `rotkehlchen/db/utils.py`; headers are validated by `validate_import_data`
 * in `rotkehlchen/utils/snapshots.py`. All rows must share the same int
 * (seconds) timestamp and the headers must appear in the exact order below
 * or the import is rejected with `'csv file has invalid headers'`.
 */

export interface BalanceRow {
  category: 'asset' | 'liability';
  assetIdentifier: string;
  amount: string;
  usdValue: string;
}

export interface LocationRow {
  location: string;
  usdValue: string;
}

const BALANCE_HEADERS = ['timestamp', 'category', 'asset_identifier', 'amount', 'usd_value'] as const;
const LOCATION_HEADERS = ['timestamp', 'location', 'usd_value'] as const;

export function generateBalancesCsv(timestamp: number, rows: BalanceRow[]): string {
  const body = rows.map(row => [
    timestamp,
    row.category,
    row.assetIdentifier,
    row.amount,
    row.usdValue,
  ].join(','));
  return [BALANCE_HEADERS.join(','), ...body].join('\n');
}

export function generateLocationDataCsv(timestamp: number, rows: LocationRow[]): string {
  const body = rows.map(row => [timestamp, row.location, row.usdValue].join(','));
  return [LOCATION_HEADERS.join(','), ...body].join('\n');
}

export interface SnapshotFixturePaths {
  balancesPath: string;
  locationsPath: string;
  cleanup: () => void;
}

/**
 * Writes the two CSVs to a unique tmp directory and returns the paths plus a
 * cleanup hook. The caller must invoke `cleanup()` from `afterAll` to remove
 * the temp dir.
 */
export function writeFixturesToTmp(
  timestamp: number,
  balanceRows: BalanceRow[],
  locationRows: LocationRow[],
): SnapshotFixturePaths {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'rotki-snapshot-'));
  const balancesPath = path.join(dir, 'balances_snapshot_import.csv');
  const locationsPath = path.join(dir, 'location_data_snapshot.csv');
  fs.writeFileSync(balancesPath, generateBalancesCsv(timestamp, balanceRows));
  fs.writeFileSync(locationsPath, generateLocationDataCsv(timestamp, locationRows));
  return {
    balancesPath,
    locationsPath,
    cleanup: (): void => {
      fs.rmSync(dir, { recursive: true, force: true });
    },
  };
}
