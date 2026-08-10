import type { EvmChainInfo, SupportedChains } from '@/modules/core/api/types/chains';
import { Blockchain } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import '@test/i18n';

const h = vi.hoisted(() => ({
  queryBlockchainBalances: vi.fn(),
}));

vi.mock('@/modules/core/notifications/use-notifications-store', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({}),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (error: unknown): string => String(error),
  useNotifications: vi.fn(() => ({ notifyError: vi.fn() })),
}));

vi.mock('@/modules/balances/use-balances-store', () => ({
  useBalancesStore: vi.fn().mockReturnValue({ updateBalances: vi.fn() }),
}));

vi.mock('@/modules/balances/api/use-blockchain-balances-api', () => ({
  useBlockchainBalancesApi: vi.fn(() => ({
    queryBlockchainBalances: h.queryBlockchainBalances,
    queryXpubBalances: vi.fn().mockResolvedValue({ taskId: 3 }),
    refreshBlockchainBalances: vi.fn().mockResolvedValue({ taskId: 4 }),
  })),
}));

vi.mock('@/modules/assets/amount-display/use-usd-value-threshold', async () => {
  const { computed } = await import('vue');
  return { useValueThreshold: vi.fn(() => computed<string | undefined>(() => undefined)) };
});

vi.mock('@/modules/core/common/use-supported-chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      getChainName: (chain: string): string => chain,
      supportedChains: computed<SupportedChains>(() => [
        {
          evmChainName: 'ethereum',
          id: Blockchain.ETH,
          image: '',
          name: 'Ethereum',
          nativeToken: 'ETH',
          type: 'evm',
        } satisfies EvmChainInfo,
        { id: Blockchain.BTC, image: '', name: 'Bitcoin', type: 'bitcoin' },
        {
          evmChainName: 'optimism',
          id: 'optimism',
          image: '',
          name: 'Optimism',
          nativeToken: 'ETH',
          type: 'evm',
        } satisfies EvmChainInfo,
      ]),
    }),
  };
});

const EMPTY_BALANCES = { perAccount: {}, totals: { assets: {}, liabilities: {} } };

/** `createSharedComposable` caches per module registry, so each test gets a fresh one. */
async function importModule(): Promise<typeof import('./use-balance-hydration')> {
  vi.resetModules();
  return import('./use-balance-hydration');
}

function addAccount(chain: string): void {
  useBlockchainAccountsStore().updateAccounts(chain, [
    createAccount(
      { address: '0x49ff149D649769033d43783E7456F626862CD160', label: null, tags: null },
      { chain, nativeAsset: 'ETH' },
    ),
  ]);
}

describe('useBalanceHydration', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();
    h.queryBlockchainBalances.mockResolvedValue(EMPTY_BALANCES);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should read only the chains that have accounts', async () => {
    const { useBalanceHydration } = await importModule();
    await useBalanceHydration().hydrate();

    expect(h.queryBlockchainBalances).not.toHaveBeenCalled();

    addAccount(Blockchain.ETH);
    await useBalanceHydration().hydrate();

    expect(h.queryBlockchainBalances).toHaveBeenCalledTimes(1);
    expect(h.queryBlockchainBalances).toHaveBeenCalledWith(
      { addresses: undefined, blockchain: Blockchain.ETH, isXpub: false },
      undefined,
    );
  });

  /**
   * ⭐ Dedup by subject. Two callers racing the same chain share one read — the guarantee
   * `submitTask`'s id dedup used to provide before hydration stopped being an activity.
   */
  it('should share one read between callers racing the same chain', async () => {
    addAccount(Blockchain.ETH);
    let release = (): void => {};
    h.queryBlockchainBalances.mockImplementation(async () => {
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      return EMPTY_BALANCES;
    });

    const { useBalanceHydration } = await importModule();
    const { hydrate } = useBalanceHydration();
    const first = hydrate({ blockchain: Blockchain.ETH });
    const second = hydrate({ blockchain: Blockchain.ETH });
    await flushPromises();

    expect(h.queryBlockchainBalances).toHaveBeenCalledTimes(1);

    release();
    await Promise.all([first, second]);
  });

  /**
   * 🔴 `allWithConcurrency` short-circuits on the first `err`: in-flight factories finish and no
   * new ones start. A chain whose read throws would take every chain that had not started with it,
   * silently. The factories are infallible for exactly this.
   */
  it('should read every chain even when one read throws', async () => {
    addAccount(Blockchain.ETH);
    addAccount(Blockchain.BTC);
    addAccount('optimism');
    h.queryBlockchainBalances.mockImplementation(async (payload: { blockchain: string }) => {
      if (payload.blockchain === Blockchain.ETH)
        throw new Error('boom');

      return EMPTY_BALANCES;
    });

    const { useBalanceHydration } = await importModule();
    await useBalanceHydration().hydrate();

    expect(h.queryBlockchainBalances).toHaveBeenCalledWith(
      expect.objectContaining({ blockchain: Blockchain.BTC }),
      undefined,
    );
    expect(h.queryBlockchainBalances).toHaveBeenCalledWith(
      expect.objectContaining({ blockchain: 'optimism' }),
      undefined,
    );
  });

  /** §1: hydration's failure policy is to retry, silently. */
  it('should retry an actionable failure', async () => {
    addAccount(Blockchain.ETH);
    h.queryBlockchainBalances
      .mockRejectedValueOnce(new Error('nope'))
      .mockResolvedValueOnce(EMPTY_BALANCES);

    const { useBalanceHydration } = await importModule();
    await useBalanceHydration().hydrate({ blockchain: Blockchain.ETH });

    expect(h.queryBlockchainBalances).toHaveBeenCalledTimes(2);
  });

  /**
   * 🔴 `retry` takes no predicate, so without the actionable check a logout mid-walk would retry
   * every chain twice more against a session that is gone.
   */
  it('should not retry a cancelled read', async () => {
    addAccount(Blockchain.ETH);
    h.queryBlockchainBalances.mockRejectedValue(new DOMException('session ended', 'AbortError'));

    const { useBalanceHydration } = await importModule();
    await useBalanceHydration().hydrate({ blockchain: Blockchain.ETH });

    expect(h.queryBlockchainBalances).toHaveBeenCalledTimes(1);
  });

  /**
   * 🔴 Hydration is not an activity, so the orchestrator cannot report it. Every spinner that used
   * to read `useIsActive(BLOCKCHAIN_BALANCES)` for the cached phase reads this instead; if it were
   * never set the whole phase would render as settled-and-empty.
   */
  it('should report liveness while a chain is being read', async () => {
    addAccount(Blockchain.ETH);
    let release = (): void => {};
    h.queryBlockchainBalances.mockImplementation(async () => {
      await new Promise<void>((resolve) => {
        release = resolve;
      });
      return EMPTY_BALANCES;
    });

    const { useBalanceHydration } = await importModule();
    const { useBalanceRefreshState } = await import('./use-balance-refresh-state');
    const refreshState = useBalanceRefreshState();

    expect(get(refreshState.isHydrating)).toBe(false);

    const read = useBalanceHydration().hydrate({ blockchain: Blockchain.ETH });
    await flushPromises();

    expect(get(refreshState.isHydrating)).toBe(true);
    expect(get(refreshState.hydratingChains).has(Blockchain.ETH)).toBe(true);

    release();
    await read;

    expect(get(refreshState.isHydrating)).toBe(false);
  });
});
