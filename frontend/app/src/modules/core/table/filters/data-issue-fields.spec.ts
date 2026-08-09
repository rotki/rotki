import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { assert } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { type DataIssueFieldResolution, toDataIssueFields } from '@/modules/core/table/filters/data-issue-fields';
import { DisplayKinds, type FieldDef, type ValueDisplay, type ValueIcon } from '@/modules/core/table/pill/core/types';
import { DataIssuesFilterKeys, DataIssuesFilterValueKeys, type Matcher } from '@/modules/history/data-issues/use-data-issues-filter';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers = {
  formatDate: (value: string): string => `date(${value})`,
  parseDate: (): string | undefined => undefined,
  resolveAssetChain: (): string | undefined => 'base',
  resolveAssetSymbol: (): string => 'DAI',
  resolveChainName: (value: string): string => value,
  resolveHex: (): string => '0x12…3456',
  resolveLocationName: (value: string): string => value,
  resolveProtocolName: (value: string): string => value,
  resolveTokenName: (value: string): string => value,
};

const resolution: DataIssueFieldResolution = {
  account: {
    resolveCaption: (value: string): string | undefined => (value.startsWith('0x') ? '0x9531...1306' : undefined),
    resolveDisplay: (value: string): ValueDisplay | undefined => (value.startsWith('0x')
      ? { kind: DisplayKinds.ADDRESS }
      : { kind: DisplayKinds.LOCATION, source: 'kraken' }),
    resolveKeywords: (value: string): string | undefined => `${value} keywords`,
    resolveLabel: (value: string): string => (value.startsWith('0x') ? 'My account' : value),
    resolveLoading: (): boolean => false,
    suggest: (): string[] => ['0x9531C059098e3d194fF87FebB587aB07B30B1306', 'Kraken 1'],
  },
  resolveKindIcon: (): ValueIcon | undefined => ({ color: 'error', icon: 'lu-trending-down' }),
  resolveKindLabel: (): string => 'Negative balance',
  resolveStateIcon: (): ValueIcon | undefined => ({ color: 'warning', icon: 'lu-circle-dot' }),
  resolveStateLabel: (): string => 'Open',
};

const matchers: Matcher[] = [
  {
    description: 'filter by state',
    key: DataIssuesFilterKeys.STATE,
    keyValue: DataIssuesFilterValueKeys.STATE,
    multiple: true,
    string: true,
    suggestions: (): string[] => ['open'],
    validate: (): boolean => true,
  },
  {
    description: 'filter by kind',
    key: DataIssuesFilterKeys.KIND,
    keyValue: DataIssuesFilterValueKeys.KIND,
    multiple: true,
    string: true,
    suggestions: (): string[] => ['negative_balance'],
    validate: (): boolean => true,
  },
  {
    asset: true,
    description: 'filter by asset',
    key: DataIssuesFilterKeys.ASSET,
    keyValue: DataIssuesFilterValueKeys.ASSET,
    suggestions: async (): Promise<string[]> => [],
  },
  {
    description: 'filter by account',
    key: DataIssuesFilterKeys.ACCOUNT,
    keyValue: DataIssuesFilterValueKeys.ACCOUNT,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
  {
    description: 'filter by start date',
    key: DataIssuesFilterKeys.START,
    keyValue: DataIssuesFilterValueKeys.START,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
  {
    description: 'filter by end date',
    key: DataIssuesFilterKeys.END,
    keyValue: DataIssuesFilterValueKeys.END,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
];

/** The one field under test, asserted rather than narrowed: its absence is a failure, not a case. */
function fieldOf(key: string): FieldDef {
  const field = toDataIssueFields(matchers, resolvers, t, resolution).find(item => item.key === key);
  assert(field);
  return field;
}

describe('toDataIssueFields', () => {
  it('should collapse the two date matchers into one period field', () => {
    const fields = toDataIssueFields(matchers, resolvers, t, resolution);

    expect(fields.map(field => field.key)).toStrictEqual(['state', 'kind', 'asset', 'locationLabel', 'period']);
  });

  it('should keep the wire keys the table already sends for the period bounds', () => {
    const period = fieldOf('period');

    expect(period.bounds).toStrictEqual({ lower: 'fromTimestamp', upper: 'toTimestamp' });
    expect(period.formatBound?.('1700000000')).toBe('date(1700000000)');
  });

  it('should label the state and kind values rather than show their wire form', () => {
    const [state, kind] = toDataIssueFields(matchers, resolvers, t, resolution);

    expect(state.resolveLabel?.('open')).toBe('Open');
    expect(state.resolveIcon?.('open')).toStrictEqual({ color: 'warning', icon: 'lu-circle-dot' });
    expect(kind.resolveLabel?.('negative_balance')).toBe('Negative balance');
    expect(kind.resolveIcon?.('negative_balance')).toStrictEqual({ color: 'error', icon: 'lu-trending-down' });
  });

  it('should draw the asset as an asset', () => {
    const asset = fieldOf('asset');

    expect(asset.display).toBe(DisplayKinds.ASSET);
    expect(asset.resolveLabel?.('eip155:1/erc20:0x6B17')).toBe('DAI');
  });

  it('should let the account be picked from the accounts the history knows', () => {
    const account = fieldOf('locationLabel');

    // Picked, not written: the matcher offers nothing, the option list does.
    expect(account.freeText).toBeUndefined();
    expect(account.suggest?.()).toStrictEqual(['0x9531C059098e3d194fF87FebB587aB07B30B1306', 'Kraken 1']);
    expect(account.resolveLabel?.('0x9531C059098e3d194fF87FebB587aB07B30B1306')).toBe('My account');
    expect(account.resolveLabel?.('Kraken 1')).toBe('Kraken 1');
  });

  it('should draw each account in its own kind, since one can be an exchange', () => {
    const account = fieldOf('locationLabel');

    // No field-wide display: the kind is per value, since `locationLabel` is an address on a chain
    // and an exchange account name elsewhere. A blockie would claim the name is an address.
    expect(account.display).toBeUndefined();
    expect(account.resolveDisplay?.('0x9531C059098e3d194fF87FebB587aB07B30B1306')).toStrictEqual({
      kind: DisplayKinds.ADDRESS,
    });
    expect(account.resolveDisplay?.('Kraken 1')).toStrictEqual({ kind: DisplayKinds.LOCATION, source: 'kraken' });
  });
});
