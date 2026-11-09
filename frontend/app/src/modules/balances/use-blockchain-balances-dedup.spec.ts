import type { RefreshMode } from '@/modules/balances/types/refresh-mode';
import type { EvmChainInfo, SupportedChains } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { WaitingReason } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

const NEW_ADDRESS = '0x0000000000000000000000000000000000000001';
const OTHER_ADDRESS = '0x0000000000000000000000000000000000000002';
const BTC_ADDRESS = 'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq';

const handler = vi.hoisted(() => ({
  runTask: vi.fn<(task: () => Promise<{ taskId: number }>) => Promise<unknown>>(),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: (): Record<string, unknown> => ({
    cancelTaskById: vi.fn(async () => true),
    runTask: handler.runTask,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({ notify: vi.fn() }),
}));

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn(() => ({ detectForChain: vi.fn(async () => {}) })),
}));

vi.mock('@/modules/balances/api/use-blockchain-balances-api', () => ({
  useBlockchainBalancesApi: vi.fn().mockReturnValue({
    queryBlockchainBalances: vi.fn(),
    queryXpubBalances: vi.fn(),
    refreshBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 4 }),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      getChain: (chain: string) => chain,
      getChainAccountType: () => 'evm',
      getChainImageUrl: (chain: string) => `${chain}.png`,
      getChainName: () => 'Ethereum',
      getNativeAsset: (chain: string) => chain,
      supportedChains: computed<SupportedChains>(() => [
        { evmChainName: 'ethereum', id: Blockchain.ETH, image: '', name: 'Ethereum', nativeToken: 'ETH', type: 'evm' } satisfies EvmChainInfo,
        { id: Blockchain.BTC, image: '', name: 'Bitcoin', type: 'bitcoin' },
      ]),
    }),
  };
});

describe('same-chain refreshes through the real native task', () => {
  let api: ReturnType<typeof useBlockchainBalancesApi>;
  let finishers: (() => void)[];
  let finishEverything: boolean;
  let refreshes: Promise<void>[];

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    api = useBlockchainBalancesApi();
    finishers = [];
    finishEverything = false;
    refreshes = [];
    const accounts = useBlockchainAccountsStore();
    accounts.updateAccounts(Blockchain.ETH, [createAccount({ address: OTHER_ADDRESS, label: null, tags: null }, Blockchain.ETH)]);
    accounts.updateAccounts(Blockchain.BTC, [createAccount({ address: BTC_ADDRESS, label: null, tags: null }, Blockchain.BTC)]);
    handler.runTask.mockImplementation(async (task) => {
      await task();
      if (!finishEverything) {
        await new Promise<void>((resolve) => {
          finishers.push(resolve);
        });
      }
      return ok({ perAccount: { eth: {} }, totals: { assets: {}, liabilities: {} } });
    });
  });

  afterEach(async () => {
    finishEverything = true;
    finishers.forEach(finish => finish());
    await Promise.allSettled(refreshes);
  });

  /** Each backend query in order, as its chain and addresses. `full` is the whole chain. */
  function queries(): string[] {
    return vi.mocked(api.refreshBlockchainBalances).mock.calls.map(([{ addresses, blockchain }]) =>
      `${blockchain}:${addresses?.join('+') ?? 'full'}`);
  }

  function refresh(addresses?: string[], blockchain: string = Blockchain.ETH, mode: RefreshMode = 'background'): void {
    refreshes.push(useBlockchainBalances().refreshBlockchainBalances({ addresses, blockchain }, mode));
  }

  async function expectQueries(expected: string[]): Promise<void> {
    await vi.waitFor(() => {
      expect(queries()).toStrictEqual(expected);
    });
  }

  function waitingReasons(): (string | undefined)[] {
    return get(useTaskOrchestrator().activities)
      .filter(activity => activity.waiting !== undefined)
      .map(activity => activity.waiting?.reason);
  }

  /** The scheduler has decided: the job it held back says so. */
  async function expectHeldBySameChain(): Promise<void> {
    await vi.waitFor(() => {
      expect(waitingReasons()).toContain(WaitingReason.SAME_CHAIN);
    });
  }

  async function finishNextQuery(): Promise<void> {
    await vi.waitFor(() => {
      expect(finishers.length).toBeGreaterThan(0);
    });
    finishers.shift()?.();
  }

  it('should query a new address once the full refresh it waited on finishes', async () => {
    refresh();
    await expectQueries(['eth:full']);

    refresh([NEW_ADDRESS]);
    await expectHeldBySameChain();
    expect(queries()).toStrictEqual(['eth:full']);

    await finishNextQuery();
    await expectQueries(['eth:full', `eth:${NEW_ADDRESS}`]);
  });

  it('should query the whole chain once the targeted refresh it waited on finishes', async () => {
    refresh([NEW_ADDRESS]);
    await expectQueries([`eth:${NEW_ADDRESS}`]);

    refresh();
    await expectHeldBySameChain();
    expect(queries()).toStrictEqual([`eth:${NEW_ADDRESS}`]);

    await finishNextQuery();
    await expectQueries([`eth:${NEW_ADDRESS}`, 'eth:full']);
  });

  it('should run only one of two same-chain jobs submitted in the same tick', async () => {
    refresh();
    refresh([NEW_ADDRESS]);
    await expectQueries(['eth:full']);
    await expectHeldBySameChain();

    expect(queries()).toStrictEqual(['eth:full']);
  });

  it('should leave the lane slot free for another chain while a job waits on its own chain', async () => {
    refresh();
    await expectQueries(['eth:full']);

    refresh([NEW_ADDRESS]);
    refresh(undefined, Blockchain.BTC);

    await expectQueries(['eth:full', 'btc:full']);
  });

  it('should skip a periodic tick that found the chain busy, not query once the chain is free', async () => {
    refresh([NEW_ADDRESS]);
    await expectQueries([`eth:${NEW_ADDRESS}`]);

    refresh(undefined, Blockchain.ETH, 'periodic');
    await expectHeldBySameChain();
    await finishNextQuery();
    await Promise.all(refreshes);

    expect(queries()).toStrictEqual([`eth:${NEW_ADDRESS}`]);
  });

  it('should still join a running refresh of the same addresses, in any order', async () => {
    refresh([NEW_ADDRESS, OTHER_ADDRESS]);
    await expectQueries([`eth:${NEW_ADDRESS}+${OTHER_ADDRESS}`]);

    refresh([OTHER_ADDRESS, NEW_ADDRESS]);
    await finishNextQuery();
    await Promise.all(refreshes);

    expect(queries()).toStrictEqual([`eth:${NEW_ADDRESS}+${OTHER_ADDRESS}`]);
  });

  it('should still join a running full refresh with another full refresh', async () => {
    refresh();
    await expectQueries(['eth:full']);

    refresh();
    await finishNextQuery();
    await Promise.all(refreshes);

    expect(queries()).toStrictEqual(['eth:full']);
  });
});
