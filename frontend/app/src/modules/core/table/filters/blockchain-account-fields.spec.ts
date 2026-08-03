import type { SearchMatcher } from '@/modules/core/table/filtering';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { type TagFieldOption, toAccountTagsField, toBlockchainAccountFields } from '@/modules/core/table/filters/blockchain-account-fields';

const t = (key: string): string => key;

const resolvers: SharedFieldResolvers & { t: (key: string) => string } = {
  formatDate: (value: string): string => `date:${value}`,
  parseDate: (value: string): string | undefined => `ts:${value}`,
  resolveAssetChain: (): string | undefined => undefined,
  resolveAssetSymbol: (value: string): string => `symbol:${value}`,
  resolveChainName: (value: string): string => `chain:${value}`,
  resolveHex: (value: string): string => `hex:${value}`,
  resolveLocationName: (value: string): string => `location:${value}`,
  resolveProtocolName: (value: string): string => `protocol:${value}`,
  resolveTokenName: (value: string): string => `token:${value}`,
  t,
};

function matcher(key: string, multiple = false): SearchMatcher<string, string> {
  return {
    description: `filter by ${key}`,
    key,
    keyValue: key,
    multiple,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  };
}

describe('toBlockchainAccountFields', () => {
  it('should draw the chain field with its chain logo and name', () => {
    const [field] = toBlockchainAccountFields([matcher('chain', true)], resolvers);
    expect(field).toMatchObject({
      display: 'chain',
      key: 'chain',
      label: 'account_balances.filter_field_labels.chain',
      multiple: true,
    });
    expect(field.resolveLabel?.('optimism')).toBe('chain:optimism');
  });

  it('should leave a field it does not know alone', () => {
    const [field] = toBlockchainAccountFields([matcher('other')], resolvers);
    expect(field).toMatchObject({ key: 'other', label: 'filter by other' });
    expect(field.display).toBeUndefined();
  });
});

describe('toAccountTagsField', () => {
  const tags: TagFieldOption[] = [
    { name: 'office', swatch: { background: '#ffffff', foreground: '#000000' } },
  ];

  it('should bind the tags field to the tags param', () => {
    const field = toAccountTagsField(t, () => tags);
    expect(field).toMatchObject({
      binding: { kind: 'param', paramKey: 'tags', to: 'both' },
      key: 'tags',
      label: 'account_balances.filter_field_labels.tags',
      multiple: true,
    });
  });

  it('should offer every tag as a value', () => {
    const field = toAccountTagsField(t, () => tags);
    expect(field.suggest?.()).toStrictEqual(['office']);
  });

  it('should resolve a tag to the colours it is recognised by', () => {
    const field = toAccountTagsField(t, () => tags);
    expect(field.resolveSwatch?.('office')).toStrictEqual({ background: '#ffffff', foreground: '#000000' });
    expect(field.resolveSwatch?.('unknown')).toBeUndefined();
  });
});
