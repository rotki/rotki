import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { assert } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { DisplayKinds, type FieldDef, type ValueDisplay, type ValueIcon } from '@/modules/core/table/pill/core/types';
import { type DataIssueFieldResolution, toDataIssueFields } from '@/modules/history/data-issues/data-issue-fields';

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

const searchAsset = async (): Promise<AssetsWithId> => [];

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
  searchAsset,
};

const fields = (): FieldDef[] => toDataIssueFields(resolvers, t, resolution);

/** The one field under test, asserted rather than narrowed: its absence is a failure, not a case. */
function fieldOf(key: string): FieldDef {
  const field = fields().find(item => item.key === key);
  assert(field);
  return field;
}

describe('toDataIssueFields', () => {
  it('should send the two date bounds as one period field', () => {
    expect(fields().map(field => field.key)).toStrictEqual(['state', 'kind', 'asset', 'locationLabel', 'period']);
  });

  it('should keep the wire keys the table already sends for the period bounds', () => {
    const period = fieldOf('period');

    expect(period.bounds).toStrictEqual({ lower: 'fromTimestamp', upper: 'toTimestamp' });
    expect(period.formatBound?.('1700000000')).toBe('date(1700000000)');
  });

  it('should label the state and kind values rather than show their wire form', () => {
    const [state, kind] = fields();

    expect(state.resolveLabel?.('open')).toBe('Open');
    expect(state.resolveIcon?.('open')).toStrictEqual({ color: 'warning', icon: 'lu-circle-dot' });
    expect(kind.resolveLabel?.('negative_balance')).toBe('Negative balance');
    expect(kind.resolveIcon?.('negative_balance')).toStrictEqual({ color: 'error', icon: 'lu-trending-down' });
  });

  it('should offer the states and kinds the app knows, and apply only those, more than one at a time', () => {
    const [state, kind] = fields();

    expect(state.multiple).toBe(true);
    expect(state.suggest?.()).toContain('open');
    expect(state.validate?.('open')).toBe(true);
    expect(state.validate?.('made_up')).toBe(false);
    expect(kind.multiple).toBe(true);
    expect(kind.validate?.('made_up')).toBe(false);
  });

  it('should draw the asset as an asset, searched rather than listed', () => {
    const asset = fieldOf('asset');

    expect(asset.display).toBe(DisplayKinds.ASSET);
    expect(asset.valueType).toBe('asset');
    expect(asset.resolveLabel?.('eip155:1/erc20:0x6B17')).toBe('DAI');
    expect(asset.searchAsset).toBe(searchAsset);
  });

  it('should let the account be picked from the accounts the history knows', () => {
    const account = fieldOf('locationLabel');

    // Picked, not written: the field offers nothing of its own, the option list does.
    expect(account.freeText).toBeUndefined();
    expect(account.suggest?.()).toStrictEqual(['0x9531C059098e3d194fF87FebB587aB07B30B1306', 'Kraken 1']);
    expect(account.resolveLabel?.('0x9531C059098e3d194fF87FebB587aB07B30B1306')).toBe('My account');
    expect(account.resolveLabel?.('Kraken 1')).toBe('Kraken 1');
  });

  it('should apply an account the option list has not loaded yet, since a value restored from the URL can arrive before the list is fetched', () => {
    const account = fieldOf('locationLabel');

    expect(account.validate?.('Kraken 1')).toBe(true);
    expect(account.validate?.('')).toBe(false);
  });

  it('should draw each account in its own kind, since one can be an exchange name rather than an address and a blockie would claim otherwise', () => {
    const account = fieldOf('locationLabel');

    expect(account.display).toBeUndefined();
    expect(account.resolveDisplay?.('0x9531C059098e3d194fF87FebB587aB07B30B1306')).toStrictEqual({
      kind: DisplayKinds.ADDRESS,
    });
    expect(account.resolveDisplay?.('Kraken 1')).toStrictEqual({ kind: DisplayKinds.LOCATION, source: 'kraken' });
  });

  it('should offer no exclusion on any field, since the request has no form for one', () => {
    for (const field of fields()) {
      expect(field.allowExclusion).toBe(false);
      expect(field.operators).not.toContain('is_not');
    }
  });
});
