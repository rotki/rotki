import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import { useAccountDelete } from '@/composables/accounts/blockchain/use-account-delete';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { bigNumberify } from '@rotki/common';
import { beforeAll, describe, expect, it } from 'vitest';

describe('useAccountDelete', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
  });

  it('should remove any accounts and and balances from state', () => {
    const accountStore = useBlockchainAccountsStore();
    const store = useBalancesStore();
    const { removeAccounts } = useAccountDelete();

    const account: BlockchainAccount<AddressData> = {
      chain: 'eth',
      data: {
        address: '0x123',
        type: 'address',
      },
      nativeAsset: 'ETH',
    };

    const balances = {
      '0x123': {
        assets: {
          ETH: {
            amount: bigNumberify(1),
            usdValue: bigNumberify(2501),
          },
        },
        liabilities: {},
      },
    };

    accountStore.updateAccounts('eth', [account]);

    store.updateBalances('eth', {
      perAccount: {
        eth: balances,
      },
      totals: {
        assets: {
          ETH: {
            amount: bigNumberify(1),
            usdValue: bigNumberify(2501),
          },
        },
        liabilities: {},
      },
    });
    expect(accountStore.accounts).toMatchObject({ eth: [account] });
    expect(store.balances).toMatchObject({ eth: balances });
    removeAccounts({ addresses: ['0x123'], chains: ['eth'] });
    expect(accountStore.accounts).toMatchObject({ eth: [] });
    expect(store.balances).toMatchObject({ eth: {} });
  });
});
