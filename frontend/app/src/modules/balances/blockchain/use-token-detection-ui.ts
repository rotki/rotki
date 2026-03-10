import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { EthDetectedTokensInfo, EvmTokensRecord } from '@/types/balances';
import type { BlockchainAssetBalances } from '@/types/blockchain/balances';
import { useSupportedChains } from '@/composables/info/chains';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { useTokenDetectionStore } from '@/modules/balances/blockchain/use-token-detection-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { arrayify } from '@/utils/array';

function noTokens(): EthDetectedTokensInfo {
  return {
    timestamp: null,
    tokens: [],
    total: 0,
  };
}

function getTokens(chainBalances: BlockchainAssetBalances, address: string, isAssetIgnored: (id: string) => boolean): string[] {
  const assets = chainBalances?.[address]?.assets ?? [];
  return Object.keys(assets).filter(id => !isAssetIgnored(id));
}

function resolveDetectedTokensInfo(
  blockchain: string,
  addr: string | null,
  tokensState: Record<string, EvmTokensRecord>,
  balances: Record<string, BlockchainAssetBalances>,
  supportsTransactions: (chain: string) => boolean,
  isAssetIgnored: (id: string) => boolean,
): EthDetectedTokensInfo {
  if (!supportsTransactions(blockchain))
    return noTokens();

  const detected: EvmTokensRecord | undefined = tokensState[blockchain];

  if (!addr)
    return noTokens();

  const info = detected?.[addr];
  if (!info)
    return noTokens();

  const tokens: string[] = getTokens(balances[blockchain], addr, isAssetIgnored);
  return {
    timestamp: info.lastUpdateTimestamp ?? null,
    tokens,
    total: tokens.length,
  };
}

interface UseTokenDetectionUiReturn {
  detectingTokens: ComputedRef<boolean>;
  detectedTokens: ComputedRef<EthDetectedTokensInfo>;
  useEthDetectedTokensInfo: (chain: MaybeRefOrGetter<string>, address: MaybeRefOrGetter<string | null>) => ComputedRef<EthDetectedTokensInfo>;
  detectTokens: (addresses?: string[]) => Promise<void>;
  detectTokensOfAllAddresses: () => Promise<void>;
}

export function useTokenDetectionUi(
  chain: MaybeRefOrGetter<string | string[]>,
  accountAddress: MaybeRefOrGetter<string | null> = null,
): UseTokenDetectionUiReturn {
  const { tokensState } = storeToRefs(useTokenDetectionStore());
  const { balances } = storeToRefs(useBalancesStore());
  const { isAssetIgnored } = useAssetsStore();
  const { supportsTransactions } = useSupportedChains();
  const { detectAllTokens, detectTokens: orchestratorDetect, useIsDetecting } = useTokenDetectionOrchestrator();

  const chains = computed<string[]>(() => arrayify(toValue(chain)));
  const detectingTokens = useIsDetecting(chain, accountAddress);

  function findDetectedTokensInfo(blockchain: string, address: string | null): EthDetectedTokensInfo {
    return resolveDetectedTokensInfo(blockchain, address, get(tokensState), get(balances), supportsTransactions, isAssetIgnored);
  }

  const detectedTokens = computed<EthDetectedTokensInfo>(() => {
    const chainsValue = get(chains);
    let totalTokens = 0;
    let latestTimestamp: number | null = null;
    const allTokens: string[] = [];

    for (const blockchain of chainsValue) {
      const info = findDetectedTokensInfo(blockchain, toValue(accountAddress));
      totalTokens += info.total;
      allTokens.push(...info.tokens);

      if (info.timestamp !== null && (latestTimestamp === null || info.timestamp > latestTimestamp))
        latestTimestamp = info.timestamp;
    }

    return {
      timestamp: latestTimestamp,
      tokens: allTokens,
      total: totalTokens,
    };
  });

  const useEthDetectedTokensInfo = (
    infoChain: MaybeRefOrGetter<string>,
    address: MaybeRefOrGetter<string | null>,
  ): ComputedRef<EthDetectedTokensInfo> => computed<EthDetectedTokensInfo>(() =>
    findDetectedTokensInfo(toValue(infoChain), toValue(address)),
  );

  const detectTokens = async (addresses: string[] = []): Promise<void> => {
    const address = toValue(accountAddress);
    const usedAddresses = address ? [address] : addresses;
    if (usedAddresses.length === 0)
      return;

    await orchestratorDetect(get(chains), usedAddresses);
  };

  const detectTokensOfAllAddresses = async (): Promise<void> => {
    await detectAllTokens(get(chains));
  };

  return {
    detectedTokens,
    detectingTokens,
    detectTokens,
    detectTokensOfAllAddresses,
    useEthDetectedTokensInfo,
  };
}
