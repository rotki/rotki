import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { type TagFieldOption, toAccountChainField, toAccountTagsField } from '@/modules/core/table/filters/blockchain-account-fields';

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

describe('toAccountChainField', () => {
  it('should bind the chain field to the chain param', () => {
    const field = toAccountChainField(t, resolvers, () => ['eth', 'optimism']);
    expect(field).toMatchObject({
      binding: { kind: 'param', paramKey: 'chain', to: 'both' },
      key: 'chain',
      label: 'account_balances.filter_field_labels.chain',
      multiple: true,
    });
  });

  it('should draw a chain with its logo and display name', () => {
    const field = toAccountChainField(t, resolvers, () => ['optimism']);
    expect(field.display).toBe('chain');
    expect(field.resolveLabel?.('optimism')).toBe('chain:optimism');
  });

  it('should offer the chains of the shown category', () => {
    const field = toAccountChainField(t, resolvers, () => ['eth', 'optimism']);
    expect(field.suggest?.()).toStrictEqual(['eth', 'optimism']);
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
