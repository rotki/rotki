import { Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type AccountManageState, createNewBlockchainAccount } from '@/modules/accounts/blockchain/use-account-manage';
import { useAccountFormWarnings } from '@/modules/accounts/management/use-account-form-warnings';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';

const {
  apiKeys,
  beaconRpcEndpoint,
  defaultEvmIndexerOrder,
  evmIndexersOrder,
  isEarlyIntegrationChain,
  isEvm,
  isSolanaChains,
  txEvmChains,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    apiKeys: ref<Record<string, string>>({}),
    beaconRpcEndpoint: ref<string>(''),
    defaultEvmIndexerOrder: ref<string[]>([]),
    evmIndexersOrder: ref<Record<string, string[]>>({}),
    isEarlyIntegrationChain: vi.fn<(chain: string) => boolean>(() => false),
    isEvm: vi.fn<(chain: string) => boolean>(() => false),
    isSolanaChains: vi.fn<(chain: string) => boolean>(() => false),
    txEvmChains: ref<{ evmChainName: string; id: string }[]>([]),
  };
});

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): Record<string, unknown> => ({
    isEarlyIntegrationChain,
    isEvm,
    isSolanaChains,
    txEvmChains,
  }),
}));

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: (): Record<string, unknown> => ({
    getApiKey: (name: string): string => get(apiKeys)[name] ?? '',
  }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (key: string): unknown => {
    if (key === 'evmIndexersOrder')
      return evmIndexersOrder;
    if (key === 'defaultEvmIndexerOrder')
      return defaultEvmIndexerOrder;
    return beaconRpcEndpoint;
  },
}));

function adding(chain: string): AccountManageState {
  return { ...createNewBlockchainAccount(), chain };
}

function addingValidator(): AccountManageState {
  return { chain: Blockchain.ETH2, data: {}, mode: 'add', type: 'validator' };
}

function editing(chain: string): AccountManageState {
  return { chain, data: { address: '0x9531C059098e3d194fF87FebB587aB07B30B1306', tags: null }, mode: 'edit', type: 'account' };
}

describe('useAccountFormWarnings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(apiKeys, {});
    set(beaconRpcEndpoint, '');
    set(defaultEvmIndexerOrder, [EvmIndexer.ETHERSCAN, EvmIndexer.BLOCKSCOUT]);
    set(evmIndexersOrder, {});
    set(txEvmChains, [{ evmChainName: 'ethereum', id: Blockchain.ETH }]);
    isEarlyIntegrationChain.mockReturnValue(false);
    isEvm.mockReturnValue(false);
    isSolanaChains.mockReturnValue(false);
  });

  /** An account being edited already exists, so there is no key the user is about to walk into. */
  it('should warn about nothing while editing', () => {
    isEvm.mockReturnValue(true);
    isEarlyIntegrationChain.mockReturnValue(true);

    const { beaconchainInfo, warnings } = useAccountFormWarnings(editing(Blockchain.ETH));

    expect(get(warnings)).toEqual([]);
    expect(get(beaconchainInfo)).toBeUndefined();
  });

  describe('the indexer key on an evm chain', () => {
    beforeEach(() => {
      isEvm.mockReturnValue(true);
    });

    it('should name etherscan when it leads and has no key', () => {
      const { warnings } = useAccountFormWarnings(adding(Blockchain.ETH));

      expect(get(warnings)).toEqual([{ service: 'etherscan', type: 'apiKey' }]);
    });

    /** With etherscan keyed, the fallback indexer is the one that would be queried keyless. */
    it('should name blockscout once etherscan is keyed', () => {
      set(apiKeys, { etherscan: 'key' });

      const { warnings } = useAccountFormWarnings(adding(Blockchain.ETH));

      expect(get(warnings)).toEqual([{ service: 'blockscout', type: 'apiKey' }]);
    });

    it('should stay quiet once both are keyed', () => {
      set(apiKeys, { blockscout: 'key', etherscan: 'key' });

      const { warnings } = useAccountFormWarnings(adding(Blockchain.ETH));

      expect(get(warnings)).toEqual([]);
    });

    /** A chain that does not put etherscan first never queries it, so a missing key costs nothing. */
    it('should stay quiet when etherscan does not lead for that chain', () => {
      set(evmIndexersOrder, { ethereum: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] });

      const { warnings } = useAccountFormWarnings(adding(Blockchain.ETH));

      expect(get(warnings)).toEqual([]);
    });

    it('should fall back to the default order for a chain with no order of its own', () => {
      set(defaultEvmIndexerOrder, [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN]);

      const { warnings } = useAccountFormWarnings(adding(Blockchain.ETH));

      expect(get(warnings)).toEqual([]);
    });

    it('should stay quiet on a chain that is not evm', () => {
      isEvm.mockReturnValue(false);

      const { warnings } = useAccountFormWarnings(adding(Blockchain.BTC));

      expect(get(warnings)).toEqual([]);
    });
  });

  /** Adding to every chain at once queries whichever of them leads with etherscan. */
  describe('adding to all chains', () => {
    it('should warn when any evm chain leads with etherscan', () => {
      set(txEvmChains, [
        { evmChainName: 'ethereum', id: Blockchain.ETH },
        { evmChainName: 'optimism', id: 'optimism' },
      ]);
      set(evmIndexersOrder, { ethereum: [EvmIndexer.BLOCKSCOUT, EvmIndexer.ETHERSCAN] });

      const { warnings } = useAccountFormWarnings(adding('all'));

      expect(get(warnings)).toContainEqual({ service: 'etherscan', type: 'apiKey' });
    });

    it('should stay quiet about keys when none of them do', () => {
      set(evmIndexersOrder, { ethereum: [EvmIndexer.BLOCKSCOUT] });

      const { warnings } = useAccountFormWarnings(adding('all'));

      expect(get(warnings)).not.toContainEqual({ service: 'etherscan', type: 'apiKey' });
    });

    it('should warn that binance chain is queried through etherscan', () => {
      const { warnings } = useAccountFormWarnings(adding('all'));

      expect(get(warnings)).toContainEqual({ type: 'binance' });
    });
  });

  describe('a solana chain', () => {
    beforeEach(() => {
      isSolanaChains.mockReturnValue(true);
    });

    it('should ask for a helius key when there is none', () => {
      const { warnings } = useAccountFormWarnings(adding('solana'));

      expect(get(warnings)).toContainEqual({ service: 'helius', type: 'apiKey' });
    });

    it('should stop asking once helius is keyed', () => {
      set(apiKeys, { helius: 'key' });

      const { warnings } = useAccountFormWarnings(adding('solana'));

      expect(get(warnings)).not.toContainEqual({ service: 'helius', type: 'apiKey' });
    });

    it('should still explain what adding a solana account does', () => {
      set(apiKeys, { helius: 'key' });

      const { warnings } = useAccountFormWarnings(adding('solana'));

      expect(get(warnings)).toEqual([{ type: 'solana' }]);
    });
  });

  /**
   * The beaconchain notice is informational rather than a warning, so it renders on its own and is
   * kept out of the warning list.
   */
  describe('a validator', () => {
    it('should name the consensus rpc when neither a key nor an endpoint is set', () => {
      const { beaconchainInfo, warnings } = useAccountFormWarnings(addingValidator());

      expect(get(beaconchainInfo)).toEqual({ service: 'consensusRpc', type: 'apiKey' });
      expect(get(warnings)).toEqual([]);
    });

    it('should name beaconchain once an endpoint is configured', () => {
      set(beaconRpcEndpoint, 'https://example.invalid');

      const { beaconchainInfo } = useAccountFormWarnings(addingValidator());

      expect(get(beaconchainInfo)).toEqual({ service: 'beaconchain', type: 'apiKey' });
    });

    it('should say nothing once beaconchain is keyed', () => {
      set(apiKeys, { beaconchain: 'key' });

      const { beaconchainInfo } = useAccountFormWarnings(addingValidator());

      expect(get(beaconchainInfo)).toBeUndefined();
    });
  });

  it('should warn that a chain is an early integration', () => {
    isEarlyIntegrationChain.mockReturnValue(true);

    const { warnings } = useAccountFormWarnings(adding('scroll'));

    expect(get(warnings)).toContainEqual({ chain: 'scroll', type: 'earlyChain' });
  });

  /** Several warnings at once are collapsed to the first, so the form is not buried in alerts. */
  describe('collapsing several warnings', () => {
    function several(): ReturnType<typeof useAccountFormWarnings> {
      isEvm.mockReturnValue(true);
      isEarlyIntegrationChain.mockReturnValue(true);
      return useAccountFormWarnings(adding(Blockchain.ETH));
    }

    it('should show a lone warning in full', () => {
      isEarlyIntegrationChain.mockReturnValue(true);

      const { hasMultipleWarnings, hiddenWarningCount, visibleWarnings, warnings } = useAccountFormWarnings(adding('scroll'));

      expect(get(warnings)).toHaveLength(1);
      expect(get(hasMultipleWarnings)).toBe(false);
      expect(get(visibleWarnings)).toEqual(get(warnings));
      expect(get(hiddenWarningCount)).toBe(0);
    });

    it('should show only the first of several', () => {
      const { hasMultipleWarnings, hiddenWarningCount, visibleWarnings, warnings } = several();

      expect(get(warnings)).toHaveLength(2);
      expect(get(hasMultipleWarnings)).toBe(true);
      expect(get(visibleWarnings)).toEqual([get(warnings)[0]]);
      expect(get(hiddenWarningCount)).toBe(1);
    });

    it('should show the rest once expanded', () => {
      const { hiddenWarningCount, toggleWarningExpanded, visibleWarnings, warnings } = several();

      toggleWarningExpanded();

      expect(get(visibleWarnings)).toEqual(get(warnings));
      expect(get(hiddenWarningCount)).toBe(0);
    });

    it('should collapse again on a second toggle', () => {
      const { toggleWarningExpanded, visibleWarnings, warningExpanded } = several();

      toggleWarningExpanded();
      toggleWarningExpanded();

      expect(get(warningExpanded)).toBe(false);
      expect(get(visibleWarnings)).toHaveLength(1);
    });
  });
});
