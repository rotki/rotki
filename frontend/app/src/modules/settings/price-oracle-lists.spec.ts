import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { CURRENT_PRICE_ORACLE_ITEMS, HISTORICAL_PRICE_ORACLE_ITEMS } from '@/modules/settings/price-oracle-lists';

/**
 * Cross-checks the oracle choices offered in the price oracle settings against the
 * backend enums, so that the UI can never offer an oracle the backend rejects
 * (e.g. "Invalid current price oracles given: alchemy").
 *
 * Backend enum members serialize to their lowercased name with underscores turned
 * into spaces (SerializableEnumNameMixin), which is what the frontend sends as the
 * oracle identifier.
 */

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../../..');

function serializedEnumName(member: string): string {
  return member.toLowerCase().replaceAll('_', ' ');
}

function backendSettableCurrentOracles(): Set<string> {
  const source = readFileSync(path.join(repoRoot, 'rotkehlchen/oracles/structures.py'), 'utf-8');
  const block = source.match(/SETTABLE_CURRENT_PRICE_ORACLES\s*=\s*\{([^}]*)\}/);
  if (!block)
    throw new Error('Could not find SETTABLE_CURRENT_PRICE_ORACLES in rotkehlchen/oracles/structures.py');

  return new Set(Array.from(block[1].matchAll(/CurrentPriceOracle\.([A-Z0-9_]+)/g), match => serializedEnumName(match[1])));
}

function backendHistoricalOracles(): Set<string> {
  const source = readFileSync(path.join(repoRoot, 'rotkehlchen/history/types.py'), 'utf-8');
  const block = source.match(/class HistoricalPriceOracle\([^)]*\):([\s\S]*?)\n\n/);
  if (!block)
    throw new Error('Could not find HistoricalPriceOracle in rotkehlchen/history/types.py');

  return new Set(Array.from(block[1].matchAll(/^ {4}([A-Z0-9_]+) = \d+$/gm), match => serializedEnumName(match[1])));
}

function identifiers(items: typeof CURRENT_PRICE_ORACLE_ITEMS): string[] {
  return items.map(item => item.identifier);
}

describe('price-oracle-lists', () => {
  it('should offer exactly the oracles the backend accepts for latest prices', () => {
    const backendOracles = backendSettableCurrentOracles();
    expect(backendOracles.size).toBeGreaterThan(0);
    expect(new Set(identifiers(CURRENT_PRICE_ORACLE_ITEMS))).toEqual(backendOracles);
  });

  it('should only offer valid backend oracles for historic prices', () => {
    const backendOracles = backendHistoricalOracles();
    expect(backendOracles.size).toBeGreaterThan(0);
    for (const identifier of identifiers(HISTORICAL_PRICE_ORACLE_ITEMS))
      expect(backendOracles, `${identifier} is not a valid HistoricalPriceOracle`).toContain(identifier);
  });
});
