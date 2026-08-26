import type {
  AddressData,
  BlockchainAccount,
  BlockchainAccountGroupWithBalance,
  XpubData,
} from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { err, ok, type Result } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

/**
 * The wiring `use-account-delete.spec.ts` cannot see: there `useAccountRemovals` is mocked away, so
 * the real submission path — activity id, orchestrator, backend outcome — never runs, and the
 * branch a single-chain group takes (`toPayload` returns `type: 'account'`) is not covered at all.
 * That is the branch behind "deleting the only EVM account leaves the row in the table".
 */

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

// The handler backs the runner the facade binds to each activity; the orchestrator stays real.
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

const account: BlockchainAccount<AddressData> = {
  chain: 'eth',
  data: { address: ADDRESS, type: 'address' },
  nativeAsset: 'ETH',
};

/** The row the EVM accounts table renders for an address tracked on one chain only. */
function singleChainGroup(): BlockchainAccountGroupWithBalance<AddressData> {
  return {
    category: 'evm',
    chains: ['eth'],
    data: { address: ADDRESS, type: 'address' },
    type: 'group',
    value: bigNumberify(0),
  };
}

/**
 * Omitting `allChains` makes the group "showing all its chains", which deletes agnostically in one
 * call; naming more chains than are shown makes it delete chain by chain.
 */
function multiChainGroup(chains: string[], allChains?: string[]): BlockchainAccountGroupWithBalance<AddressData> {
  return {
    allChains,
    category: 'evm',
    chains,
    data: { address: ADDRESS, type: 'address' },
    type: 'group',
    value: bigNumberify(0),
  };
}

function xpubGroup(): BlockchainAccountGroupWithBalance<XpubData> {
  return {
    category: 'btc',
    chains: ['btc'],
    data: { type: 'xpub', xpub: XPUB },
    type: 'group',
    value: bigNumberify(0),
  };
}

/** What the backend task reports back for this removal. The API call itself always goes out. */
function backendReports(outcome: Result<unknown, TaskError>): void {
  mocks.runTask.mockImplementation(async (task: () => Promise<unknown>): Promise<Result<unknown, TaskError>> => {
    await task();
    return outcome;
  });
}

/**
 * Fails only the named chains. The verdict is derived from each task's own API call rather than
 * from a shared variable, so the chain-by-chain removals — which are submitted together — cannot
 * read each other's outcome.
 */
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

function accountOn(chain: string): BlockchainAccount<AddressData> {
  return { chain, data: { address: ADDRESS, type: 'address' }, nativeAsset: chain.toUpperCase() };
}

interface Harness {
  accounts: ReturnType<typeof import('@/modules/accounts/use-blockchain-accounts-store')['useBlockchainAccountsStore']>;
  confirmRemoval: (row: BlockchainAccountGroupWithBalance<AddressData> | BlockchainAccountGroupWithBalance<XpubData>) => Promise<void>;
  /** The chain read the periodic balance tick performs, `use-balance-fetching.ts` one level up. */
  fetchChain: (chain: string) => Promise<void>;
}

/**
 * `useNativeTask` is a `createSharedComposable`, so every test needs its own module graph, or the
 * orchestrator (and its in-flight map) leaks between them and the second submit of an id is deduped
 * onto the first test's promise.
 */
async function setup(): Promise<Harness> {
  vi.resetModules();
  setActivePinia(createPinia());

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
    vi.clearAllMocks();
    backendReports(ok(undefined));
  });

  it('should delete the only account of a single-chain group and drop it from the store', async () => {
    const { accounts, confirmRemoval } = await setup();

    await confirmRemoval(singleChainGroup());

    expect(mocks.removeBlockchainAccount).toHaveBeenCalledWith('eth', [ADDRESS]);
    expect(accounts.accounts).toStrictEqual({ eth: [] });
  });

  // The removals return `Promise<void>` and swallow their `Result` after notifying, so the caller
  // cannot tell a failed delete from a successful one and drops the row either way. The account
  // still exists on the backend, and nothing on this path ever re-reads to put it back.
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

    // no `allChains`, so the group shows every chain it has and deletes in one agnostic call
    await confirmRemoval(multiChainGroup(['eth', 'optimism']));

    expect(mocks.removeAgnosticBlockchainAccount).toHaveBeenCalledOnce();
    expect(accounts.accounts).toStrictEqual({ eth: [account], optimism: [accountOn('optimism')] });
  });

  it('should keep every chain when all of a chain-by-chain removal fails', async () => {
    const { accounts, confirmRemoval } = await setup();
    accounts.updateAccounts('optimism', [accountOn('optimism')]);
    backendFails(['eth', 'optimism']);

    await confirmRemoval(multiChainGroup(['eth', 'optimism'], ['eth', 'optimism', 'base']));

    expect(accounts.accounts).toStrictEqual({ eth: [account], optimism: [accountOn('optimism')] });
  });

  it('should drop only the chains whose removal succeeded', async () => {
    const { accounts, confirmRemoval } = await setup();
    accounts.updateAccounts('optimism', [accountOn('optimism')]);
    backendFails(['optimism']);

    await confirmRemoval(multiChainGroup(['eth', 'optimism'], ['eth', 'optimism', 'base']));

    // eth went through, optimism did not: dropping both would lose a row the backend still has
    expect(accounts.accounts).toStrictEqual({ eth: [], optimism: [accountOn('optimism')] });
  });

  it('should drop the xpub when its removal succeeds', async () => {
    const { accounts, confirmRemoval } = await setup();
    accounts.updateAccounts('btc', [{
      chain: 'btc',
      data: { type: 'xpub', xpub: XPUB },
      nativeAsset: 'BTC',
    }]);

    await confirmRemoval(xpubGroup());

    expect(mocks.deleteXpub).toHaveBeenCalledOnce();
    expect(accounts.accounts.btc).toStrictEqual([]);
  });

  it('should keep the xpub when its removal fails', async () => {
    const { accounts, confirmRemoval } = await setup();
    const xpubAccount: BlockchainAccount<XpubData> = {
      chain: 'btc',
      data: { type: 'xpub', xpub: XPUB },
      nativeAsset: 'BTC',
    };
    accounts.updateAccounts('btc', [xpubAccount]);
    backendReports(err(TaskFailed({ message: 'boom' })));

    await confirmRemoval(xpubGroup());

    expect(mocks.deleteXpub).toHaveBeenCalledOnce();
    expect(accounts.accounts.btc).toStrictEqual([xpubAccount]);
  });

  // The reported symptom: the row survives the delete although the backend has dropped the account.
  // The periodic balance tick (`autoRefresh`) walks every chain, and a walk that was
  // already in flight answers with a pre-delete snapshot. `updateAccounts` replaces the chain
  // wholesale, so the deleted account comes back, and the delete path has no re-read to correct it.
  it('should not let a chain read that started before the delete resurrect the account', async () => {
    const { accounts, confirmRemoval, fetchChain } = await setup();

    let answer: () => void = () => {};
    const inFlight = new Promise<void>((resolve) => {
      answer = resolve;
    });
    // The response the backend produced *before* the delete, delivered after it.
    mocks.queryAccounts.mockImplementation(async (): Promise<unknown[]> => {
      await inFlight;
      return [{ address: ADDRESS, label: null, tags: null }];
    });

    const periodicRead = fetchChain('eth');
    await confirmRemoval(singleChainGroup());
    expect(accounts.accounts.eth).toHaveLength(0);

    answer();
    await periodicRead;

    expect(accounts.accounts.eth).toHaveLength(0);
  });
});
