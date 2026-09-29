import type { AddressAccount, AddressGroupWithBalance } from '@/modules/accounts/blockchain-accounts';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { bigNumberify } from '@rotki/common';
import { ok, type Result } from 'plainfp/result';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountDelete } from '@/modules/accounts/blockchain/use-account-delete';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import '@test/i18n';

const mocks = vi.hoisted(() => ({
  deleteXpub: vi.fn(async (): Promise<Result<void, TaskError>> => ok(undefined)),
  removeAccount: vi.fn(async (_payload: { accounts: string[]; chain: string }): Promise<Result<void, TaskError>> => ok(undefined)),
  removeAgnosticAccount: vi.fn(async (): Promise<Result<void, TaskError>> => ok(undefined)),
}));

vi.mock('@/modules/accounts/use-account-removals', () => ({
  useAccountRemovals: vi.fn(() => ({
    deleteXpub: mocks.deleteXpub,
    removeAccount: mocks.removeAccount,
    removeAgnosticAccount: mocks.removeAgnosticAccount,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChainName: (chain: string): string => chain,
  })),
}));

function groupAccount(chains: string[], allChains?: string[]): AddressGroupWithBalance {
  return {
    address: '0x123',
    allChains,
    category: 'evm',
    chains,
    kind: 'address',
    type: 'group',
    value: bigNumberify(0),
  };
}

describe('useAccountDelete', () => {
  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should remove the account and its balances from the stores once the backend deletes it', async () => {
    const accountStore = useBlockchainAccountsStore();
    const store = useBalancesStore();
    const account: AddressAccount = { address: '0x123', chain: 'eth', kind: 'address' };
    const balances = {
      '0x123': {
        assets: { ETH: { address: { amount: bigNumberify(1), value: bigNumberify(2501) } } },
        liabilities: {},
      },
    };
    accountStore.updateAccounts('eth', [account]);
    store.updateBalances('eth', {
      perAccount: { eth: balances },
      totals: { assets: { ETH: { address: { amount: bigNumberify(1), value: bigNumberify(2501) } } }, liabilities: {} },
    });

    useAccountDelete().showConfirmation({ data: { ...groupAccount(['eth']) }, type: 'account' });
    await useConfirmStore().confirm();

    expect(mocks.removeAccount).toHaveBeenCalledExactlyOnceWith({ accounts: ['0x123'], chain: 'eth' });
    expect(accountStore.accounts).toMatchObject({ eth: [] });
    expect(store.balances).toMatchObject({ eth: {} });
  });

  describe('removeGroupAccounts', () => {
    const seedChains = (chains: string[]): void => {
      const accountStore = useBlockchainAccountsStore();
      for (const chain of chains) {
        accountStore.updateAccounts(chain, [{
          address: '0x123',
          chain,
          kind: 'address',
        }]);
      }
    };

    const confirmRemoval = async (account: AddressGroupWithBalance): Promise<void> => {
      const { showConfirmation } = useAccountDelete();
      showConfirmation({ data: account, type: 'account' });
      await useConfirmStore().confirm();
    };

    it('should remove a group showing all its chains agnostically', async () => {
      seedChains(['eth', 'optimism']);

      await confirmRemoval(groupAccount(['eth', 'optimism']));

      expect(mocks.removeAgnosticAccount).toHaveBeenCalledWith('evm', '0x123');
      expect(mocks.removeAccount).not.toHaveBeenCalled();
      expect(useBlockchainAccountsStore().accounts).toMatchObject({ eth: [], optimism: [] });
    });

    it('should remove a group agnostically under its own category, not always as evm', async () => {
      const accountStore = useBlockchainAccountsStore();
      const legacyAddress = '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2';
      for (const chain of ['btc', 'bch'])
        accountStore.updateAccounts(chain, [{ address: legacyAddress, chain, kind: 'address' }]);

      await confirmRemoval({ ...groupAccount(['btc', 'bch']), address: legacyAddress, category: 'bitcoin' });

      expect(mocks.removeAgnosticAccount).toHaveBeenCalledExactlyOnceWith('bitcoin', legacyAddress);
      expect(useBlockchainAccountsStore().accounts).toMatchObject({ bch: [], btc: [] });
    });

    it('should remove a partially shown group chain by chain and leave the chains it did not show', async () => {
      seedChains(['eth', 'optimism', 'base']);

      await confirmRemoval(groupAccount(['eth', 'optimism'], ['eth', 'optimism', 'base']));

      expect(mocks.removeAgnosticAccount).not.toHaveBeenCalled();
      expect(mocks.removeAccount).toHaveBeenCalledTimes(2);
      expect(mocks.removeAccount).toHaveBeenCalledWith({ accounts: ['0x123'], chain: 'eth' });
      expect(mocks.removeAccount).toHaveBeenCalledWith({ accounts: ['0x123'], chain: 'optimism' });
      expect(useBlockchainAccountsStore().accounts).toMatchObject({
        base: [{ chain: 'base' }],
        eth: [],
        optimism: [],
      });
    });

    it('should submit every chain removal before any of them settles', async () => {
      seedChains(['eth', 'optimism']);

      let release = (): void => {};
      const started: string[] = [];
      const gate = new Promise<void>((resolve) => {
        release = resolve;
      });
      mocks.removeAccount.mockImplementation(async ({ chain }: { chain: string }): Promise<Result<void, TaskError>> => {
        started.push(chain);
        await gate;
        return ok(undefined);
      });

      const removal = confirmRemoval(groupAccount(['eth', 'optimism'], ['eth', 'optimism', 'base']));
      await vi.waitFor(() => {
        expect(started).toStrictEqual(['eth', 'optimism']);
      });

      release();
      await removal;

      expect(useBlockchainAccountsStore().accounts).toMatchObject({ eth: [], optimism: [] });
    });
  });
});
