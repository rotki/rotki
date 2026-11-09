import type { SupportedChains } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useAccountAdditionService } from '@/modules/accounts/use-account-addition-service';
import { useAccountOperations } from '@/modules/accounts/use-account-operations';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';

const TRACKED = 'bc1qtracked';
const NEW_ADDRESS = 'bc1qnew';
const EVM_ADDRESS = '0x0000000000000000000000000000000000000001';

const h = vi.hoisted(() => ({
  runTask: vi.fn<(task: () => Promise<{ taskId: number }>) => Promise<unknown>>(),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: (): Record<string, unknown> => ({
    cancelTaskById: vi.fn(async () => true),
    runTask: h.runTask,
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

vi.mock('@/modules/accounts/use-account-fetching', () => ({
  useAccountFetching: vi.fn(() => ({ fetch: vi.fn(async () => {}) })),
}));

vi.mock('@/modules/accounts/use-account-additions', () => ({
  useAccountAdditions: vi.fn(() => ({ addAccount: vi.fn(), addEvmAccount: vi.fn() })),
}));

vi.mock('@/modules/accounts/address-book/use-ens-operations', () => ({
  useEnsOperations: vi.fn(() => ({ fetchEnsNames: vi.fn(async () => {}) })),
}));

vi.mock('@/modules/balances/use-balance-hydration', () => ({
  useBalanceHydration: vi.fn(() => ({ hydrate: vi.fn(async () => {}) })),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn(() => ({ enableModule: vi.fn(async () => {}) })),
}));

vi.mock('@/modules/tags/use-tag-operations', () => ({
  useTagOperations: vi.fn(() => ({ fetchTags: vi.fn(async () => {}) })),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      evmChains: computed<string[]>(() => [Blockchain.ETH, Blockchain.AVAX]),
      getChain: (chain: string) => chain,
      getChainAccountType: () => 'evm',
      getChainImageUrl: (chain: string) => `${chain}.png`,
      getChainName: (chain: string) => chain,
      getNativeAsset: (chain: string) => chain,
      isEvm: (chain: string): boolean => chain === Blockchain.ETH || chain === Blockchain.AVAX,
      supportedChains: computed<SupportedChains>(() => []),
      supportsTransactions: (chain: string): boolean => chain === Blockchain.ETH,
    }),
  };
});

describe('adding an address while its chain refreshes, through the real services', () => {
  let api: ReturnType<typeof useBlockchainBalancesApi>;
  let finishers: (() => void)[];
  let finishEverything: boolean;
  let pending: Promise<void>[];

  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    api = useBlockchainBalancesApi();
    finishers = [];
    finishEverything = false;
    pending = [];
    const accounts = useBlockchainAccountsStore();
    accounts.updateAccounts(Blockchain.BTC, [createAccount({ address: TRACKED, label: null, tags: null }, Blockchain.BTC)]);
    accounts.updateAccounts(Blockchain.ETH, [createAccount({ address: EVM_ADDRESS, label: null, tags: null }, Blockchain.ETH)]);
    accounts.updateAccounts(Blockchain.AVAX, [createAccount({ address: EVM_ADDRESS, label: null, tags: null }, Blockchain.AVAX)]);
    h.runTask.mockImplementation(async (task) => {
      await task();
      if (!finishEverything) {
        await new Promise<void>((resolve) => {
          finishers.push(resolve);
        });
      }
      return ok({ perAccount: {}, totals: { assets: {}, liabilities: {} } });
    });
  });

  afterEach(async () => {
    finishEverything = true;
    finishers.forEach(finish => finish());
    await Promise.allSettled(pending);
  });

  function queries(): string[] {
    return vi.mocked(api.refreshBlockchainBalances).mock.calls.map(([{ addresses, blockchain }]) =>
      `${blockchain}:${addresses?.join('+') ?? 'full'}`);
  }

  async function expectQueries(expected: string[]): Promise<void> {
    await vi.waitFor(() => {
      expect(queries()).toStrictEqual(expected);
    });
  }

  function completeAddition(addedAccounts: { address: string; chain: string }[], chain?: string): void {
    const { fetchAccounts, refreshAccounts } = useAccountOperations();
    pending.push(useAccountAdditionService().completeAccountAddition(
      { addedAccounts, chain },
      refreshAccounts,
      fetchAccounts,
    ));
  }

  it('should query a new address on a chain without detection once the running refresh finishes', async () => {
    pending.push(useBlockchainBalances().refreshBlockchainBalances({ blockchain: Blockchain.BTC }, 'background'));
    await expectQueries(['btc:full']);

    completeAddition([{ address: NEW_ADDRESS, chain: Blockchain.BTC }], Blockchain.BTC);
    await vi.waitFor(() => {
      expect(finishers).toHaveLength(1);
    });
    finishers.shift()?.();

    await expectQueries(['btc:full', `btc:${NEW_ADDRESS}`]);
  });

  it('should query a chain without detection when the addition spans every EVM chain', async () => {
    completeAddition([
      { address: EVM_ADDRESS, chain: Blockchain.ETH },
      { address: EVM_ADDRESS, chain: Blockchain.AVAX },
    ]);

    await vi.waitFor(() => {
      expect(queries()).toEqual(expect.arrayContaining([`avax:${EVM_ADDRESS}`, 'eth:full']));
    });
  });
});
