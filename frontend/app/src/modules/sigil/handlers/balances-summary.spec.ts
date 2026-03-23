import type { Accounts } from '@/types/blockchain/accounts';
import { beforeEach, describe, expect, it } from 'vitest';

function stubAccount(address: string): Accounts[string][number] {
  return { data: { type: 'address', address }, chain: 'eth', nativeAsset: 'ETH' };
}

describe('useBalancesSummaryHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should return empty summary with no data', async () => {
    const { useBalancesSummaryHandler } = await import('@/modules/sigil/handlers/balances-summary');
    const collect = useBalancesSummaryHandler();
    const result = collect();

    expect(result.premium).toBe(false);
    expect(result.plan).toBe('Free');
    expect(result.hasManualBalances).toBe(false);
    expect(result.totalAccounts).toBe(0);
    expect(result.totalChains).toBe(0);
    expect(result.distinctAssetCount).toBe(0);
  });

  it('should count accounts per chain', async () => {
    const { useBlockchainAccountsStore } = await import('@/modules/accounts/use-blockchain-accounts-store');
    const { accounts } = storeToRefs(useBlockchainAccountsStore());

    set(accounts, {
      eth: [stubAccount('0x1'), stubAccount('0x2')],
      btc: [stubAccount('bc1')],
    });

    const { useBalancesSummaryHandler } = await import('@/modules/sigil/handlers/balances-summary');
    const collect = useBalancesSummaryHandler();
    const result = collect();

    expect(result.totalAccounts).toBe(3);
    expect(result.totalChains).toBe(2);
    expect(result.accounts_eth).toBe(2);
    expect(result.accounts_btc).toBe(1);
  });

  it('should exclude chains with no accounts', async () => {
    const { useBlockchainAccountsStore } = await import('@/modules/accounts/use-blockchain-accounts-store');
    const { accounts } = storeToRefs(useBlockchainAccountsStore());

    set(accounts, {
      eth: [stubAccount('0x1')],
      btc: [],
      optimism: [],
    });

    const { useBalancesSummaryHandler } = await import('@/modules/sigil/handlers/balances-summary');
    const collect = useBalancesSummaryHandler();
    const result = collect();

    expect(result.totalAccounts).toBe(1);
    expect(result.totalChains).toBe(1);
    expect(result.accounts_eth).toBe(1);
    expect(result).not.toHaveProperty('accounts_btc');
    expect(result).not.toHaveProperty('accounts_optimism');
  });
});
