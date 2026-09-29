import type {
  AddressAccount,
  AddressGroupWithBalance,
  ValidatorAccount,
  XpubAccount,
  XpubGroupWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const mocks = vi.hoisted(() => ({
  cancelTaskById: vi.fn(async (): Promise<boolean> => true),
  deleteEth2Validators: vi.fn(),
  deleteXpub: vi.fn(async (): Promise<{ taskId: number }> => ({ taskId: 1 })),
  notifyError: vi.fn(),
  queryAccounts: vi.fn(),
  removeAgnosticBlockchainAccount: vi.fn(async (): Promise<{ taskId: number }> => ({ taskId: 1 })),
  removeBlockchainAccount: vi.fn(async (_chain: string, _accounts: string[]): Promise<{ taskId: number }> => ({ taskId: 1 })),
  runTask: vi.fn(),
}));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    deleteXpub: mocks.deleteXpub,
    queryAccounts: mocks.queryAccounts,
    removeAgnosticBlockchainAccount: mocks.removeAgnosticBlockchainAccount,
    removeBlockchainAccount: mocks.removeBlockchainAccount,
  })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: (): Record<string, unknown> => ({
    cancelTaskById: mocks.cancelTaskById,
    runTask: mocks.runTask,
  }),
}));

vi.mock('@/modules/accounts/use-eth-staking', () => ({
  useEthStaking: vi.fn(() => ({ deleteEth2Validators: mocks.deleteEth2Validators })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({ notifyError: mocks.notifyError })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getChainName: (chain: string): string => chain,
    getNativeAsset: (chain: string): string => chain.toUpperCase(),
  })),
}));

const ADDRESS = '0x123';
const XPUB = 'xpub123';

const account: AddressAccount = {
  address: ADDRESS,
  chain: 'eth',
  kind: 'address',
};

function singleChainGroup(): AddressGroupWithBalance {
  return {
    address: ADDRESS,
    category: 'evm',
    chains: ['eth'],
    kind: 'address',
    type: 'group',
    value: bigNumberify(0),
  };
}

function groupShowingAllChains(chains: string[]): AddressGroupWithBalance {
  return {
    address: ADDRESS,
    category: 'evm',
    chains,
    kind: 'address',
    type: 'group',
    value: bigNumberify(0),
  };
}

function groupShowingSomeChains(chains: string[], allChains: string[]): AddressGroupWithBalance {
  return {
    address: ADDRESS,
    allChains,
    category: 'evm',
    chains,
    kind: 'address',
    type: 'group',
    value: bigNumberify(0),
  };
}

function xpubGroup(): XpubGroupWithBalance {
  return {
    amount: bigNumberify(0),
    category: 'bitcoin',
    chains: ['btc'],
    kind: 'xpub',
    nativeAsset: 'BTC',
    type: 'group',
    value: bigNumberify(0),
    xpub: XPUB,
  };
}

function backendReports(outcome: Result<unknown, TaskError>): void {
  mocks.runTask.mockImplementation(async (task: () => Promise<unknown>): Promise<Result<unknown, TaskError>> => {
    await task();
    return outcome;
  });
}

function backendFails(chains: string[]): void {
  mocks.runTask.mockImplementation(async (task: () => Promise<unknown>): Promise<Result<unknown, TaskError>> => {
    try {
      await task();
      return ok(undefined);
    }
    catch {
      return err(TaskFailed({ message: 'boom' }));
    }
  });
  mocks.removeBlockchainAccount.mockImplementation(async (chain: string): Promise<{ taskId: number }> => {
    if (chains.includes(chain))
      throw new Error('boom');
    return { taskId: 1 };
  });
}

function accountOn(chain: string): AddressAccount {
  return { address: ADDRESS, chain, kind: 'address' };
}

interface Harness {
  accounts: ReturnType<typeof import('@/modules/accounts/use-blockchain-accounts-store')['useBlockchainAccountsStore']>;
  confirmRemoval: (row: AddressGroupWithBalance | XpubGroupWithBalance) => Promise<void>;
  fetchChain: (chain: string) => Promise<void>;
}

async function setup(): Promise<Harness> {
  const { useAccountDelete } = await import('@/modules/accounts/blockchain/use-account-delete');
  const { useAccountFetching } = await import('@/modules/accounts/use-account-fetching');
  const { useBlockchainAccountsStore } = await import('@/modules/accounts/use-blockchain-accounts-store');
  const { useConfirmStore } = await import('@/modules/core/common/use-confirm-store');

  const accounts = useBlockchainAccountsStore();
  accounts.updateAccounts('eth', [account]);

  const { showConfirmation } = useAccountDelete();

  return {
    accounts,
    fetchChain: useAccountFetching().fetch,
    confirmRemoval: async (row): Promise<void> => {
      showConfirmation({ data: row, type: 'account' });
      await useConfirmStore().confirm();
    },
  };
}

describe('useAccountDelete against the real removal wiring', () => {
  beforeEach(() => {
    vi.resetModules();
    setActivePinia(createPinia());
    vi.clearAllMocks();
    backendReports(ok(undefined));
  });

  it('should delete the only account of a single-chain group and drop it from the store', async () => {
    const { accounts, confirmRemoval } = await setup();

    await confirmRemoval(singleChainGroup());

    expect(mocks.removeBlockchainAccount).toHaveBeenCalledWith('eth', [ADDRESS]);
    expect(accounts.accounts).toStrictEqual({ eth: [] });
  });

  it('should keep the account when the backend removal fails', async () => {
    const { accounts, confirmRemoval } = await setup();
    backendReports(err(TaskFailed({ message: 'boom' })));

    await confirmRemoval(singleChainGroup());

    expect(mocks.notifyError).toHaveBeenCalledOnce();
    expect(accounts.accounts).toStrictEqual({ eth: [account] });
  });

  it('should keep the account when the removal is cancelled', async () => {
    const { accounts, confirmRemoval } = await setup();
    backendReports(err(Cancelled({ message: 'cancelled' })));

    await confirmRemoval(singleChainGroup());

    expect(accounts.accounts).toStrictEqual({ eth: [account] });
  });

  it('should keep the account when an agnostic group removal fails', async () => {
    const { accounts, confirmRemoval } = await setup();
    accounts.updateAccounts('optimism', [accountOn('optimism')]);
    mocks.removeAgnosticBlockchainAccount.mockRejectedValue(new Error('boom'));
    backendFails([]);

    await confirmRemoval(groupShowingAllChains(['eth', 'optimism']));

    expect(mocks.removeAgnosticBlockchainAccount).toHaveBeenCalledOnce();
    expect(accounts.accounts).toStrictEqual({ eth: [account], optimism: [accountOn('optimism')] });
  });

  it('should keep every chain when all of a chain-by-chain removal fails', async () => {
    const { accounts, confirmRemoval } = await setup();
    accounts.updateAccounts('optimism', [accountOn('optimism')]);
    backendFails(['eth', 'optimism']);

    await confirmRemoval(groupShowingSomeChains(['eth', 'optimism'], ['eth', 'optimism', 'base']));

    expect(accounts.accounts).toStrictEqual({ eth: [account], optimism: [accountOn('optimism')] });
  });

  it('should drop only the chains whose removal succeeded', async () => {
    const { accounts, confirmRemoval } = await setup();
    accounts.updateAccounts('optimism', [accountOn('optimism')]);
    backendFails(['optimism']);

    await confirmRemoval(groupShowingSomeChains(['eth', 'optimism'], ['eth', 'optimism', 'base']));

    expect(accounts.accounts).toStrictEqual({ eth: [], optimism: [accountOn('optimism')] });
  });

  it('should drop the xpub when its removal succeeds', async () => {
    const { accounts, confirmRemoval } = await setup();
    accounts.updateAccounts('btc', [{
      chain: 'btc',
      kind: 'xpub',
      xpub: XPUB,
    }]);

    await confirmRemoval(xpubGroup());

    expect(mocks.deleteXpub).toHaveBeenCalledOnce();
    expect(accounts.accounts.btc).toStrictEqual([]);
  });

  it('should keep the xpub when its removal fails', async () => {
    const { accounts, confirmRemoval } = await setup();
    const xpubAccount: XpubAccount = {
      chain: 'btc',
      kind: 'xpub',
      xpub: XPUB,
    };
    accounts.updateAccounts('btc', [xpubAccount]);
    backendReports(err(TaskFailed({ message: 'boom' })));

    await confirmRemoval(xpubGroup());

    expect(mocks.deleteXpub).toHaveBeenCalledOnce();
    expect(accounts.accounts.btc).toStrictEqual([xpubAccount]);
  });

  it('should drop only the xpub with the deleted derivation path and its derived addresses', async () => {
    const { accounts, confirmRemoval } = await setup();
    const kept: XpubAccount = { chain: 'btc', derivationPath: 'm/1', kind: 'xpub', xpub: XPUB };
    const keptChild: AddressAccount = { address: 'bc1kept', chain: 'btc', kind: 'address', xpubParent: { derivationPath: 'm/1', xpub: XPUB } };
    accounts.updateAccounts('btc', [
      { chain: 'btc', derivationPath: 'm/0', kind: 'xpub', xpub: XPUB },
      { address: 'bc1gone', chain: 'btc', kind: 'address', xpubParent: { derivationPath: 'm/0', xpub: XPUB } },
      kept,
      keptChild,
    ]);

    await confirmRemoval({ ...xpubGroup(), derivationPath: 'm/0' });

    expect(mocks.deleteXpub).toHaveBeenCalledExactlyOnceWith({ chain: 'btc', derivationPath: 'm/0', xpub: XPUB });
    expect(accounts.accounts.btc).toStrictEqual([kept, keptChild]);
  });

  describe('validators', () => {
    const validator = { index: 1, publicKey: '0xvalidator', status: 'active' };
    const stored: ValidatorAccount = { ...validator, chain: 'eth2', kind: 'validator' };

    async function confirmValidatorRemoval(): Promise<void> {
      const { useAccountDelete } = await import('@/modules/accounts/blockchain/use-account-delete');
      const { useConfirmStore } = await import('@/modules/core/common/use-confirm-store');
      useAccountDelete().showConfirmation({
        data: [{ ...validator, amount: bigNumberify(32), value: bigNumberify(32) }],
        type: 'validator',
      });
      await useConfirmStore().confirm();
    }

    it('should drop the validator when the backend deletes it', async () => {
      const { accounts } = await setup();
      accounts.updateAccounts('eth2', [stored]);
      mocks.deleteEth2Validators.mockResolvedValue(true);

      await confirmValidatorRemoval();

      expect(mocks.deleteEth2Validators).toHaveBeenCalledExactlyOnceWith([validator.publicKey]);
      expect(accounts.accounts.eth2).toStrictEqual([]);
    });

    it('should keep the validator when the backend delete fails', async () => {
      const { accounts } = await setup();
      accounts.updateAccounts('eth2', [stored]);
      mocks.deleteEth2Validators.mockResolvedValue(false);

      await confirmValidatorRemoval();

      expect(accounts.accounts.eth2).toStrictEqual([stored]);
    });
  });

  it('should not let a chain read that started before the delete resurrect the account', async () => {
    const { accounts, confirmRemoval, fetchChain } = await setup();

    let deliverStaleRead: () => void = () => {};
    const staleReadDelivered = new Promise<void>((resolve) => {
      deliverStaleRead = resolve;
    });
    mocks.queryAccounts.mockImplementation(async (): Promise<unknown[]> => {
      await staleReadDelivered;
      return [{ address: ADDRESS, label: null, tags: null }];
    });

    const periodicRead = fetchChain('eth');
    await confirmRemoval(singleChainGroup());
    expect(accounts.accounts.eth).toHaveLength(0);

    deliverStaleRead();
    await periodicRead;

    expect(accounts.accounts.eth).toHaveLength(0);
  });
});
