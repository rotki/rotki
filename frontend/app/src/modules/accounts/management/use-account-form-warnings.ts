import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AccountManageState } from '@/modules/accounts/blockchain/use-account-manage';
import { camelCase } from 'es-toolkit';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { EvmIndexer } from '@/modules/settings/types/evm-indexer';
import { useSetting } from '@/modules/settings/use-setting';

/** The services worth warning about when the account being added would query them without a key. */
type MissingKeyService = 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc' | 'blockscout';

type WarningType = 'apiKey' | 'binance' | 'earlyChain' | 'solana';

interface WarningItem {
  type: WarningType;
  service?: MissingKeyService;
  chain?: string;
}

export interface UseAccountFormWarningsReturn {
  /**
   * The beaconchain key notice, which is informational rather than a warning and so renders on its
   * own; it is therefore kept out of `warnings`.
   */
  beaconchainInfo: ComputedRef<WarningItem | undefined>;
  warnings: ComputedRef<WarningItem[]>;
  hasMultipleWarnings: ComputedRef<boolean>;
  /** The warnings to render: all of them once expanded, otherwise the first alone. */
  visibleWarnings: ComputedRef<WarningItem[]>;
  hiddenWarningCount: ComputedRef<number>;
  warningExpanded: Readonly<Ref<boolean>>;
  toggleWarningExpanded: () => void;
}

function isBeaconchainService(service: MissingKeyService | undefined): boolean {
  return service === 'beaconchain' || service === 'consensusRpc';
}

/**
 * Derives what the account form warns about before an account is added.
 *
 * @remarks
 * Nothing is warned about while editing: the account already exists, so a missing key is not
 * something the user is about to walk into.
 */
export function useAccountFormWarnings(state: MaybeRefOrGetter<AccountManageState>): UseAccountFormWarningsReturn {
  const { isEarlyIntegrationChain, isEvm, isSolanaChains, txEvmChains } = useSupportedChains();
  const { getApiKey } = useExternalApiKeys();

  const beaconRpcEndpoint = useSetting('beaconRpcEndpoint');
  const defaultEvmIndexerOrder = useSetting('defaultEvmIndexerOrder');
  const evmIndexersOrder = useSetting('evmIndexersOrder');

  const warningExpanded = shallowRef<boolean>(false);

  const chain = computed<string | undefined>(() => toValue(state).chain);
  const isAdding = computed<boolean>(() => toValue(state).mode === 'add');

  function isEtherscanTopPriority(chainId: string): boolean {
    const chainOrders = get(evmIndexersOrder);
    const evmChainName = camelCase(get(txEvmChains).find(c => c.id === chainId)?.evmChainName ?? '');
    const indexerOrder = evmChainName && chainOrders[evmChainName]
      ? chainOrders[evmChainName]
      : get(defaultEvmIndexerOrder);

    return indexerOrder[0] === EvmIndexer.ETHERSCAN;
  }

  /** For 'all', any EVM chain putting etherscan first is enough to warn. */
  function shouldShowEtherscanWarning(selectedChain: string): boolean {
    if (selectedChain === 'all')
      return get(txEvmChains).some(chain => isEtherscanTopPriority(chain.id));

    if (!isEvm(selectedChain))
      return false;

    return isEtherscanTopPriority(selectedChain);
  }

  /** Without a beaconchain key, validators fall back to a consensus RPC, which needs its own endpoint. */
  function validatorKeyService(): MissingKeyService | undefined {
    if (getApiKey('beaconchain'))
      return undefined;

    return get(beaconRpcEndpoint) ? 'beaconchain' : 'consensusRpc';
  }

  /** Both indexers are only worth warning about on chains that actually use them. */
  function indexerKeyService(chain: string): MissingKeyService | undefined {
    if (!shouldShowEtherscanWarning(chain))
      return undefined;

    if (!getApiKey('etherscan'))
      return 'etherscan';

    return getApiKey('blockscout') ? undefined : 'blockscout';
  }

  const missingApiKeyService = computed<MissingKeyService | undefined>(() => {
    const selectedChain = get(chain);
    const currentState = toValue(state);

    if (!get(isAdding) || !selectedChain)
      return undefined;

    if (currentState.type === 'validator')
      return validatorKeyService();

    if (isSolanaChains(selectedChain))
      return getApiKey('helius') ? undefined : 'helius';

    return indexerKeyService(selectedChain);
  });

  const showSolanaInitialAlert = computed<boolean>(() => {
    const selectedChain = get(chain);
    return get(isAdding) && !!selectedChain && isSolanaChains(selectedChain);
  });

  const earlyIntegrationChain = computed<string | undefined>(() => {
    const selectedChain = get(chain);

    if (get(isAdding) && selectedChain && isEarlyIntegrationChain(selectedChain))
      return selectedChain;
    return undefined;
  });

  const showBinanceEtherscanWarning = computed<boolean>(() => get(isAdding) && get(chain) === 'all');

  const beaconchainInfo = computed<WarningItem | undefined>(() => {
    const service = get(missingApiKeyService);
    if (!service || !isBeaconchainService(service))
      return undefined;
    return { service, type: 'apiKey' };
  });

  const warnings = computed<WarningItem[]>(() => {
    const result: WarningItem[] = [];
    const service = get(missingApiKeyService);
    if (service && !isBeaconchainService(service))
      result.push({ service, type: 'apiKey' });
    if (get(showSolanaInitialAlert))
      result.push({ type: 'solana' });
    const earlyChain = get(earlyIntegrationChain);
    if (earlyChain)
      result.push({ chain: earlyChain, type: 'earlyChain' });
    if (get(showBinanceEtherscanWarning))
      result.push({ type: 'binance' });
    return result;
  });

  const hasMultipleWarnings = computed<boolean>(() => get(warnings).length > 1);

  const visibleWarnings = computed<WarningItem[]>(() => {
    const all = get(warnings);
    if (all.length <= 1 || get(warningExpanded))
      return all;
    return all.slice(0, 1);
  });

  const hiddenWarningCount = computed<number>(() => get(warnings).length - get(visibleWarnings).length);

  function toggleWarningExpanded(): void {
    set(warningExpanded, !get(warningExpanded));
  }

  return {
    beaconchainInfo,
    hasMultipleWarnings,
    hiddenWarningCount,
    toggleWarningExpanded,
    visibleWarnings,
    warningExpanded: readonly(warningExpanded),
    warnings,
  };
}
