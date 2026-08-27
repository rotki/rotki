import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNewlyDetectedFields } from '@/modules/assets/detection/use-newly-detected-fields';
import { NewlyDetectedFilterKeys } from '@/modules/assets/detection/use-newly-detected-filter';
import { resolveText } from '@/modules/core/table/pill/core/text';

let addresses: Record<string, string[]> = {};

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: (): Record<string, unknown> => ({
    addresses: computed(() => addresses),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    isSolanaChains: (chain: string): boolean => chain === 'solana',
  }),
}));

describe('useNewlyDetectedFields', () => {
  beforeEach(() => {
    addresses = {};
  });

  it('should offer nothing when there is no solana account, since every detected token is then an evm one', () => {
    addresses = { eth: ['0xabc'] };

    expect(get(useNewlyDetectedFields())).toStrictEqual([]);
  });

  it('should offer nothing when the solana chain has no addresses', () => {
    addresses = { eth: ['0xabc'], solana: [] };

    expect(get(useNewlyDetectedFields())).toStrictEqual([]);
  });

  it('should offer the kind field once a solana account exists', () => {
    addresses = { solana: ['So111'] };
    const [kind] = get(useNewlyDetectedFields());

    expect(kind.key).toBe(NewlyDetectedFilterKeys.TOKEN_KIND);
    expect(resolveText(kind.label)).toBe('asset_table.newly_detected.token_type');
    expect(kind.multiple).toBe(false);
  });

  it('should offer both kinds, read as their chain families', () => {
    addresses = { solana: ['So111'] };
    const [kind] = get(useNewlyDetectedFields());

    expect(kind.suggest?.()).toStrictEqual(['evm', 'solana']);
    expect(kind.resolveLabel?.('evm')).toBe('EVM');
    expect(kind.resolveLabel?.('solana')).toBe('Solana');
  });

  it('should refuse a kind the query cannot mean', () => {
    addresses = { solana: ['So111'] };
    const [kind] = get(useNewlyDetectedFields());

    expect(kind.validate?.('evm')).toBe(true);
    expect(kind.validate?.('nonsense')).toBe(false);
  });
});
