import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { DisplayKinds, type FieldDef } from '@/modules/core/table/pill/core/types';
import { toInternalTxConflictFields } from '@/modules/history/internal-tx-conflicts/internal-tx-conflict-fields';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => `date(${value})`,
  parseDate: (): string | undefined => undefined,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (value: string): string => value,
  resolveChainName: (): string => 'Optimism',
  resolveHex: (value: string): string => value,
  resolveLocationName: (value: string): string => value,
  resolveProtocolName: (value: string): string => value,
  resolveTokenName: (value: string): string => value,
};

const chains = (): string[] => ['optimism'];

const fields = (): FieldDef[] => toInternalTxConflictFields(resolvers, t, chains);

describe('toInternalTxConflictFields', () => {
  it('should send the two date bounds as one period field', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['chain', 'period']);
  });

  it('should keep the wire keys the table already sends for the period bounds', () => {
    const [, period] = fields();

    expect(period.bounds).toStrictEqual({ lower: 'fromTimestamp', upper: 'toTimestamp' });
    expect(period.formatBound?.('1700000000')).toBe('date(1700000000)');
  });

  it('should draw the chain as the shared chain pill', () => {
    const [chain] = fields();

    expect(chain.display).toBe(DisplayKinds.CHAIN);
    expect(chain.label).toBe('internal_tx_conflicts.columns.chain');
    expect(chain.resolveLabel?.('optimism')).toBe('Optimism');
    expect(chain.suggest?.()).toStrictEqual(['optimism']);
  });

  // A conflict is on exactly one chain, and only on a chain the backend knows.
  it('should apply only one chain, and only a known one', () => {
    const [chain] = fields();

    expect(chain.multiple).toBe(false);
    expect(chain.validate?.('optimism')).toBe(true);
    expect(chain.validate?.('made_up')).toBe(false);
  });

  // Neither key is declared as behaviour-carrying, so the request has no form for an exclusion and
  // the pill must not offer one.
  it('should offer no exclusion on any field', () => {
    for (const field of fields()) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });
});
