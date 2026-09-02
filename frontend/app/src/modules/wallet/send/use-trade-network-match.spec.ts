import type { EffectScope, Ref } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeNetworkMatch } from '@/modules/wallet/send/use-trade-network-match';

const ETHEREUM_CHAIN_ID = 1;
const OPTIMISM_CHAIN_ID = 10;
const UNSUPPORTED_CHAIN_ID = 250;

const CHAIN_NAMES: Record<number, string | undefined> = {
  [ETHEREUM_CHAIN_ID]: 'eth',
  [OPTIMISM_CHAIN_ID]: 'optimism',
};
const CHAIN_IDS: Record<string, number | undefined> = {
  eth: ETHEREUM_CHAIN_ID,
  optimism: OPTIMISM_CHAIN_ID,
};

const connected = ref<boolean>(true);
const connectedChainId = ref<number>();
const switchNetwork = vi.fn<(chainId: bigint) => Promise<void>>(async () => {});
const error = vi.fn();

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: (...args: unknown[]): void => error(...args), info: vi.fn(), warn: vi.fn() },
}));

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: vi.fn(() => ({ connected, connectedChainId, switchNetwork })),
}));

vi.mock('@/modules/wallet/use-wallet-helper', () => ({
  useWalletHelper: vi.fn(() => ({
    getChainFromChainId: (chainId: number): string | undefined => CHAIN_NAMES[chainId],
    getChainIdFromChain: (chain: string): number | undefined => CHAIN_IDS[chain],
  })),
}));

describe('useTradeNetworkMatch', () => {
  let scope: EffectScope;
  let selectedChain: Ref<string>;

  function create(): ReturnType<typeof useTradeNetworkMatch> {
    scope = effectScope();
    const result = scope.run(() => useTradeNetworkMatch(selectedChain));
    assert(result);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    set(connected, true);
    set(connectedChainId, ETHEREUM_CHAIN_ID);
    selectedChain = ref<string>('eth');
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('wrongNetwork', () => {
    it('should be false while the wallet is on the selected chain', () => {
      const { wrongNetwork } = create();

      expect(get(wrongNetwork)).toBe(false);
    });

    it('should be false while no wallet is connected', () => {
      set(connected, false);
      set(connectedChainId, OPTIMISM_CHAIN_ID);
      const { wrongNetwork } = create();

      expect(get(wrongNetwork)).toBe(false);
    });

    it('should be true while the wallet is on another supported chain', () => {
      const { wrongNetwork } = create();
      set(connectedChainId, OPTIMISM_CHAIN_ID);

      expect(get(wrongNetwork)).toBe(true);
    });

    it('should be true while the wallet is on a chain rotki does not support', () => {
      const { wrongNetwork } = create();
      set(connectedChainId, UNSUPPORTED_CHAIN_ID);

      expect(get(wrongNetwork)).toBe(true);
    });
  });

  describe('following the wallet', () => {
    it('should adopt a supported chain the wallet moves to', async () => {
      create();
      set(connectedChainId, OPTIMISM_CHAIN_ID);
      await nextTick();

      expect(get(selectedChain)).toBe('optimism');
    });

    it('should leave the selection alone when the wallet reports no chain', async () => {
      create();
      set(selectedChain, 'optimism');
      // What a disconnect looks like: there is no chain to follow.
      set(connectedChainId, undefined);
      await nextTick();

      expect(get(selectedChain)).toBe('optimism');
    });

    it('should not pull the selection back while the wallet stays put', async () => {
      create();
      set(selectedChain, 'optimism');
      set(connectedChainId, ETHEREUM_CHAIN_ID);
      await nextTick();

      expect(get(selectedChain)).toBe('optimism');
    });

    it('should keep the selection when the wallet moves to an unsupported chain', async () => {
      set(connectedChainId, OPTIMISM_CHAIN_ID);
      create();
      await nextTick();
      expect(get(selectedChain)).toBe('optimism');

      set(connectedChainId, UNSUPPORTED_CHAIN_ID);
      await nextTick();

      expect(get(selectedChain)).toBe('optimism');
    });
  });

  describe('switchToSelectedChain', () => {
    it('should ask the wallet for the selected chain', () => {
      const { switchToSelectedChain } = create();
      set(selectedChain, 'optimism');

      switchToSelectedChain();

      expect(switchNetwork).toHaveBeenCalledWith(BigInt(OPTIMISM_CHAIN_ID));
    });

    it('should log rather than switch when the selection has no chain id', () => {
      const { switchToSelectedChain } = create();
      set(selectedChain, 'newchain');

      switchToSelectedChain();

      expect(switchNetwork).not.toHaveBeenCalled();
      expect(error).toHaveBeenCalledWith(expect.stringContaining('newchain'));
    });
  });
});
