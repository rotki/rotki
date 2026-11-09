import type { EvmChainInfo, SupportedChains } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';

const NEW_ADDRESS = '0x0000000000000000000000000000000000000001';
const OTHER_ADDRESS = '0x0000000000000000000000000000000000000002';

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
      ]),
    }),
  };
});

describe('same-chain refreshes through the real native task', () => {
  let api: ReturnType<typeof useBlockchainBalancesApi>;
  let release: () => void;
  let refreshes: Promise<void>[];

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    api = useBlockchainBalancesApi();
    refreshes = [];
    useBlockchainAccountsStore().updateAccounts(Blockchain.ETH, [
      createAccount({ address: OTHER_ADDRESS, label: null, tags: null }, Blockchain.ETH),
    ]);
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    handler.runTask.mockImplementation(async (task) => {
      await task();
      await gate;
      return ok({ perAccount: { eth: {} }, totals: { assets: {}, liabilities: {} } });
    });
  });

  afterEach(async () => {
    release();
    await Promise.allSettled(refreshes);
  });

  /** The addresses of each backend query, in order. `full` is a query of the whole chain. */
  function queries(): (readonly string[] | 'full')[] {
    return vi.mocked(api.refreshBlockchainBalances).mock.calls.map(([payload]) => payload.addresses ?? 'full');
  }

  function refresh(addresses?: string[]): void {
    refreshes.push(useBlockchainBalances().refreshBlockchainBalances({ addresses, blockchain: Blockchain.ETH }, 'background'));
  }

  async function expectQueries(expected: (readonly string[] | 'full')[]): Promise<void> {
    await vi.waitFor(() => {
      expect(queries()).toStrictEqual(expected);
    });
  }

  async function settle(): Promise<void> {
    release();
    await Promise.all(refreshes);
  }

  it('should query a new address even while a full refresh is running', async () => {
    refresh();
    await expectQueries(['full']);

    refresh([NEW_ADDRESS]);
    await expectQueries(['full', [NEW_ADDRESS]]);
  });

  it('should query the whole chain even while a targeted refresh is running', async () => {
    refresh([NEW_ADDRESS]);
    await expectQueries([[NEW_ADDRESS]]);

    refresh();
    await expectQueries([[NEW_ADDRESS], 'full']);
  });

  it('should still join a running refresh of the same addresses, in any order', async () => {
    refresh([NEW_ADDRESS, OTHER_ADDRESS]);
    await expectQueries([[NEW_ADDRESS, OTHER_ADDRESS]]);

    refresh([OTHER_ADDRESS, NEW_ADDRESS]);
    await settle();

    expect(queries()).toStrictEqual([[NEW_ADDRESS, OTHER_ADDRESS]]);
  });

  it('should still join a running full refresh with another full refresh', async () => {
    refresh();
    await expectQueries(['full']);

    refresh();
    await settle();

    expect(queries()).toStrictEqual(['full']);
  });
});
