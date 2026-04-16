import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTokenDetectionStore } from './use-token-detection-store';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    supportsTransactions: (chain: string): boolean => chain === 'eth' || chain === 'optimism',
  }),
}));

vi.mock('@/modules/assets/use-assets-store', () => ({
  useAssetsStore: vi.fn().mockReturnValue({
    isAssetIgnored: (id: string): boolean => id === 'IGNORED_TOKEN',
  }),
}));

vi.mock('@/modules/balances/use-balances-store', async () => {
  const { ref } = await import('vue');
  return {
    useBalancesStore: vi.fn().mockReturnValue({
      balances: ref<Record<string, Record<string, { assets: Record<string, unknown> }>>>({
        eth: {
          '0xaddr1': {
            assets: {
              ETH: { amount: '1' },
              DAI: { amount: '100' },
              IGNORED_TOKEN: { amount: '50' },
            },
          },
        },
        optimism: {
          '0xaddr2': {
            assets: {
              USDC: { amount: '200' },
            },
          },
        },
      }),
    }),
  };
});

const mockDetectTokens = vi.fn().mockResolvedValue(undefined);
const mockDetectAllTokens = vi.fn().mockResolvedValue(undefined);
const mockUseIsDetecting = vi.fn().mockReturnValue(computed(() => false));
vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: vi.fn().mockReturnValue({
    detectTokens: mockDetectTokens,
    detectAllTokens: mockDetectAllTokens,
    useIsDetecting: mockUseIsDetecting,
  }),
}));

const { useTokenDetectionUi } = await import('./use-token-detection-ui');

describe('useTokenDetectionUi', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('detectedTokens — query logic', () => {
    it('should return no tokens for unsupported chains', () => {
      const store = useTokenDetectionStore();
      store.setState('solana', { '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['SOL'] } });

      const { detectedTokens } = useTokenDetectionUi('solana', '0xaddr1');

      expect(get(detectedTokens).total).toBe(0);
      expect(get(detectedTokens).tokens).toEqual([]);
    });

    it('should return no tokens when address is null', () => {
      const store = useTokenDetectionStore();
      store.setState('eth', { '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['DAI'] } });

      const { detectedTokens } = useTokenDetectionUi('eth', null);

      expect(get(detectedTokens).total).toBe(0);
    });

    it('should return no tokens when no detection data exists for address', () => {
      const { detectedTokens } = useTokenDetectionUi('eth', '0xunknown');

      expect(get(detectedTokens).total).toBe(0);
    });

    it('should return detected tokens excluding ignored assets', () => {
      const store = useTokenDetectionStore();
      store.setState('eth', { '0xaddr1': { lastUpdateTimestamp: 1234, tokens: ['DAI'] } });

      const { detectedTokens } = useTokenDetectionUi('eth', '0xaddr1');

      expect(get(detectedTokens).tokens).toContain('ETH');
      expect(get(detectedTokens).tokens).toContain('DAI');
      expect(get(detectedTokens).tokens).not.toContain('IGNORED_TOKEN');
      expect(get(detectedTokens).total).toBe(2);
      expect(get(detectedTokens).timestamp).toBe(1234);
    });

    it('should return null timestamp when lastUpdateTimestamp is nullish', () => {
      const store = useTokenDetectionStore();
      store.setState('eth', { '0xaddr1': { lastUpdateTimestamp: null, tokens: ['DAI'] } });

      const { detectedTokens } = useTokenDetectionUi('eth', '0xaddr1');

      expect(get(detectedTokens).timestamp).toBeNull();
    });

    it('should aggregate tokens across multiple chains', () => {
      const store = useTokenDetectionStore();
      store.setState('eth', { '0xaddr1': { lastUpdateTimestamp: 1000, tokens: ['DAI'] } });
      store.setState('optimism', { '0xaddr2': { lastUpdateTimestamp: 2000, tokens: ['USDC'] } });

      const chainRef = ref<string[]>(['eth', 'optimism']);
      const addrRef = ref<string | null>(null);

      // Use per-chain address lookup — eth has 0xaddr1, optimism has 0xaddr2
      // With null accountAddress, detectedTokens returns noTokens for each chain
      const { detectedTokens } = useTokenDetectionUi(chainRef, addrRef);
      expect(get(detectedTokens).total).toBe(0);

      // Set address to 0xaddr1 — only eth chain will match
      set(addrRef, '0xaddr1');
      expect(get(detectedTokens).tokens).toContain('ETH');
      expect(get(detectedTokens).tokens).toContain('DAI');
      expect(get(detectedTokens).timestamp).toBe(1000);
    });

    it('should use the latest timestamp across chains', () => {
      const store = useTokenDetectionStore();
      store.setState('eth', { '0xaddr1': { lastUpdateTimestamp: 5000, tokens: ['DAI'] } });
      store.setState('optimism', { '0xaddr1': { lastUpdateTimestamp: 3000, tokens: ['USDC'] } });

      const { detectedTokens } = useTokenDetectionUi(['eth', 'optimism'], '0xaddr1');

      expect(get(detectedTokens).timestamp).toBe(5000);
    });
  });

  describe('useEthDetectedTokensInfo', () => {
    it('should return a reactive computed of detection info', () => {
      const store = useTokenDetectionStore();
      store.setState('eth', { '0xaddr1': { lastUpdateTimestamp: 5000, tokens: ['DAI'] } });

      const { useEthDetectedTokensInfo } = useTokenDetectionUi('eth');
      const info = useEthDetectedTokensInfo('eth', '0xaddr1');

      expect(get(info).timestamp).toBe(5000);
      expect(get(info).total).toBe(2); // ETH + DAI (IGNORED_TOKEN filtered)

      // Update state and verify reactivity
      store.setState('eth', { '0xaddr1': { lastUpdateTimestamp: 6000, tokens: ['DAI', 'USDC'] } });

      expect(get(info).timestamp).toBe(6000);
    });
  });

  describe('detectTokens', () => {
    it('should call orchestrator with account address when set', async () => {
      const { detectTokens } = useTokenDetectionUi('eth', '0xaddr1');

      await detectTokens();

      expect(mockDetectTokens).toHaveBeenCalledWith(['eth'], ['0xaddr1']);
    });

    it('should call orchestrator with provided addresses when no account address', async () => {
      const { detectTokens } = useTokenDetectionUi('eth');

      await detectTokens(['0xaddr1', '0xaddr2']);

      expect(mockDetectTokens).toHaveBeenCalledWith(['eth'], ['0xaddr1', '0xaddr2']);
    });

    it('should not call orchestrator when no addresses available', async () => {
      const { detectTokens } = useTokenDetectionUi('eth');

      await detectTokens();

      expect(mockDetectTokens).not.toHaveBeenCalled();
    });

    it('should prefer account address over provided addresses', async () => {
      const { detectTokens } = useTokenDetectionUi('eth', '0xfixed');

      await detectTokens(['0xother']);

      expect(mockDetectTokens).toHaveBeenCalledWith(['eth'], ['0xfixed']);
    });
  });

  describe('detectTokensOfAllAddresses', () => {
    it('should call detectAllTokens with current chains', async () => {
      const { detectTokensOfAllAddresses } = useTokenDetectionUi(['eth', 'optimism']);

      await detectTokensOfAllAddresses();

      expect(mockDetectAllTokens).toHaveBeenCalledWith(['eth', 'optimism']);
    });
  });

  describe('detectingTokens', () => {
    it('should delegate to orchestrator useIsDetecting', () => {
      mockUseIsDetecting.mockReturnValue(computed(() => true));

      const { detectingTokens } = useTokenDetectionUi('eth', '0xaddr1');

      expect(get(detectingTokens)).toBe(true);
      expect(mockUseIsDetecting).toHaveBeenCalled();
    });
  });
});
