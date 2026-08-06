import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toInternalTxConflictFields } from '@/modules/core/table/filters/internal-tx-conflict-fields';
import { DisplayKinds } from '@/modules/core/table/pill/core/types';
import { InternalTxConflictFilterKeys, InternalTxConflictFilterValueKeys, type Matcher } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts-filter';

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

const matchers: Matcher[] = [
  {
    description: 'filter by chain',
    key: InternalTxConflictFilterKeys.CHAIN,
    keyValue: InternalTxConflictFilterValueKeys.CHAIN,
    string: true,
    suggestions: (): string[] => ['optimism'],
    validate: (value: string): boolean => value === 'optimism',
  },
  {
    description: 'filter by start date',
    key: InternalTxConflictFilterKeys.FROM_TIMESTAMP,
    keyValue: InternalTxConflictFilterValueKeys.FROM_TIMESTAMP,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
  {
    description: 'filter by end date',
    key: InternalTxConflictFilterKeys.TO_TIMESTAMP,
    keyValue: InternalTxConflictFilterValueKeys.TO_TIMESTAMP,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
];

describe('toInternalTxConflictFields', () => {
  it('should collapse the two date matchers into one period field', () => {
    expect(toInternalTxConflictFields(matchers, resolvers, t).map(field => field.key)).toStrictEqual([
      'chain',
      'period',
    ]);
  });

  it('should keep the wire keys the table already sends for the period bounds', () => {
    const [, period] = toInternalTxConflictFields(matchers, resolvers, t);

    expect(period.bounds).toStrictEqual({ lower: 'fromTimestamp', upper: 'toTimestamp' });
    expect(period.formatBound?.('1700000000')).toBe('date(1700000000)');
  });

  it('should draw the chain as the shared chain pill', () => {
    const [chain] = toInternalTxConflictFields(matchers, resolvers, t);

    expect(chain.display).toBe(DisplayKinds.CHAIN);
    expect(chain.label).toBe('internal_tx_conflicts.columns.chain');
    expect(chain.resolveLabel?.('optimism')).toBe('Optimism');
    expect(chain.suggest?.()).toStrictEqual(['optimism']);
  });
});
