import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { dataDir } from '../../../playwright.config';

const SEED_SCRIPT = path.resolve(import.meta.dirname, '..', 'scripts', 'seed-db.py');

interface SeedInsert {
  table: string;
  columns: string[];
  values: (string | number | null)[];
  conflict?: 'ignore' | 'replace';
}

/**
 * Generic runner — sends JSON seed instructions to the Python script via stdin.
 * When a password is provided, opens the DB with SQLCipher (user DB).
 * When omitted, opens with plain sqlite3 (global DB).
 */
function runSeedScript(dbPath: string, inserts: SeedInsert[], password?: string): void {
  const payload = JSON.stringify({ inserts });
  const args = ['run', 'python', SEED_SCRIPT, dbPath];
  if (password)
    args.push(password);

  const result = spawnSync('uv', args, { input: payload, encoding: 'utf-8' });

  if (result.stderr)
    console.warn('seed-db stderr:', result.stderr);

  if (result.status !== 0)
    throw new Error(`seed-db.py exited with code ${result.status}: ${result.stderr}`);
}

function seedUserDatabase(username: string, inserts: SeedInsert[], password: string = '1234'): void {
  const dbPath = path.join(dataDir, 'users', username, 'rotkehlchen.db');
  runSeedScript(dbPath, inserts, password);
}

/**
 * Seeds an EVM transaction row into the user's encrypted DB.
 */
export function seedEvmTransaction(
  username: string,
  txHash: string,
  chainId: number = 1,
  password: string = '1234',
): void {
  const hashHex = txHash.replace(/^0x/, '');

  seedUserDatabase(username, [{
    table: 'evm_transactions',
    columns: [
      'tx_hash',
      'chain_id',
      'timestamp',
      'block_number',
      'from_address',
      'to_address',
      'value',
      'gas',
      'gas_price',
      'gas_used',
      'input_data',
      'nonce',
    ],
    values: [
      `<hex:${hashHex}>`,
      chainId,
      1650276061,
      14608535,
      '0x57bF3B0f29E37619623994071C9e12091919675c',
      '0xDeBF20617708857ebe4F679508E7b7863a8A8EeE',
      '0',
      '171249',
      '22990000000',
      '171249',
      '<hex:>',
      0,
    ],
    conflict: 'ignore',
  }], password);
}

function seedGlobalDatabase(inserts: SeedInsert[]): void {
  const dbPath = path.join(dataDir, 'global', 'global.db');
  runSeedScript(dbPath, inserts);
}

/**
 * Seeds historic prices into the global DB for a list of assets at a given timestamp.
 * Uses source_type 'A' (MANUAL) so these prices are always preferred.
 */
export function seedHistoricPrices(
  assets: { fromAsset: string; price: string }[],
  timestamp: number,
  toAsset: string = 'USD',
): void {
  const inserts: SeedInsert[] = assets.map(({ fromAsset, price }) => ({
    table: 'price_history',
    columns: [
      'from_asset',
      'to_asset',
      'source_type',
      'timestamp',
      'price',
    ],
    values: [
      fromAsset,
      toAsset,
      'A',
      timestamp,
      price,
    ],
    conflict: 'replace',
  }));

  seedGlobalDatabase(inserts);
}
