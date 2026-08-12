import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { describe, expect, it } from 'vitest';
import { toAccountChainField } from '@/modules/accounts/blockchain-account-fields';
import { resolveText } from '@/modules/core/table/pill/core/text';

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
      multiple: true,
    });
    expect(resolveText(field.label)).toBe('account_balances.filter_field_labels.chain');
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
