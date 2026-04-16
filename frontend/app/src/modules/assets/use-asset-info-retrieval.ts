import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { ERC20Token } from '@/modules/accounts/blockchain-accounts';
import type { TaskMeta } from '@/modules/core/tasks/types';
import type { EvmChainAddress } from '@/modules/history/events/event-payloads';
import {
  type AssetInfoWithId,
  getAddressFromEvmIdentifier,
  getAddressFromSolanaIdentifier,
  getNftAssetIdDetail,
  isEvmIdentifier,
  isEvmIdentifierWithNftId,
  isSolanaTokenIdentifier,
  NotificationGroup,
  Severity,
} from '@rotki/common';
import { type AssetSearchParams, useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { type AssetsWithId, EVM_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { processAssetInfo, useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { isAbortError } from '@/modules/core/common/helpers/is-of-enum';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';

export interface AssetResolutionOptions {
  associate?: boolean;
  collectionParent?: boolean;
}

export const NO_COLLECTION_RESOLVE: AssetResolutionOptions = { collectionParent: false } as const;

interface AssetWithResolutionStatus extends AssetInfoWithId {
  resolved: boolean;
}

interface AssetContractInfo {
  location: string;
  address: string;
  nftId?: string;
}

export type AssetStringField = 'symbol' | 'name';

export type PlainAssetInfoReturn = (identifier: string | undefined, options?: AssetResolutionOptions) => AssetWithResolutionStatus | null;

export type AssetInfoReturn = (identifier: MaybeRefOrGetter<string | undefined>, options?: MaybeRefOrGetter<AssetResolutionOptions>) => ComputedRef<AssetWithResolutionStatus | null>;

type PlainAssetContractInfoReturn = (identifier: string | undefined, options?: AssetResolutionOptions) => AssetContractInfo | undefined;

type AssetContractInfoReturn = (identifier: MaybeRefOrGetter<string | undefined>, options?: MaybeRefOrGetter<AssetResolutionOptions>) => ComputedRef<AssetContractInfo | undefined>;

interface UseAssetInfoRetrievalReturn {
  assetSearch: (params: AssetSearchParams) => Promise<AssetsWithId>;
  fetchTokenDetails: (payload: EvmChainAddress) => Promise<ERC20Token>;
  getAssetContractInfo: PlainAssetContractInfoReturn;
  getAssetField: (identifier: string | undefined, field: AssetStringField, options?: AssetResolutionOptions) => string;
  getAssetInfo: PlainAssetInfoReturn;
  getTokenAddress: (identifier: string, options?: AssetResolutionOptions) => string;
  refetchAssetInfo: (key: string) => void;
  useAssetContractInfo: AssetContractInfoReturn;
  useAssetField: (identifier: MaybeRefOrGetter<string | undefined>, field: AssetStringField, options?: MaybeRefOrGetter<AssetResolutionOptions>) => ComputedRef<string>;
  useAssetInfo: AssetInfoReturn;
  useTokenAddress: (identifier: MaybeRefOrGetter<string>, options?: MaybeRefOrGetter<AssetResolutionOptions>) => ComputedRef<string>;
}

export function useAssetInfoRetrieval(): UseAssetInfoRetrievalReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { assetSearch: assetSearchCaller, erc20details } = useAssetInfoApi();
  const { fetchedAssetCollections, queueIdentifier, resolve: resolveAsset } = useAssetInfoCache();
  const { notify, notifyError } = useNotifications();
  const { runTask } = useTaskHandler();

  const { getChain } = useSupportedChains();

  const resolveAssetIdentifier = useResolveAssetIdentifier();

  const getAssetInfo: PlainAssetInfoReturn = (
    identifier: string | undefined,
    options: AssetResolutionOptions = {},
  ): AssetWithResolutionStatus | null => {
    if (!identifier)
      return null;

    const {
      associate = true,
      collectionParent = true,
    } = options;

    const key = associate ? resolveAssetIdentifier(identifier) : identifier;
    const data = resolveAsset(key);

    const collectionData = collectionParent && data?.collectionId
      ? get(fetchedAssetCollections)[data.collectionId]
      : null;

    const processedInfo = processAssetInfo(data, identifier, collectionData);

    if (!processedInfo) {
      return null;
    }

    return {
      ...processedInfo,
      identifier: key,
      resolved: !!data,
    };
  };

  const useAssetInfo: AssetInfoReturn = (
    identifier: MaybeRefOrGetter<string | undefined>,
    options: MaybeRefOrGetter<AssetResolutionOptions> = {},
  ): ComputedRef<AssetWithResolutionStatus | null> =>
    computed<AssetWithResolutionStatus | null>(() => getAssetInfo(toValue(identifier), toValue(options)));

  const getAssetField = (
    identifier: string | undefined,
    field: AssetStringField,
    options?: AssetResolutionOptions,
  ): string => {
    if (!identifier)
      return '';
    return getAssetInfo(identifier, options)?.[field] ?? '';
  };

  const useAssetField = (
    identifier: MaybeRefOrGetter<string | undefined>,
    field: AssetStringField,
    options?: MaybeRefOrGetter<AssetResolutionOptions>,
  ): ComputedRef<string> =>
    computed<string>(() => getAssetField(toValue(identifier), field, toValue(options)));

  const getAssetContractInfo: PlainAssetContractInfoReturn = (
    identifier: string | undefined,
    options?: AssetResolutionOptions,
  ): AssetContractInfo | undefined => {
    if (!identifier)
      return undefined;

    const asset = getAssetInfo(identifier, options);

    if (!asset)
      return undefined;

    const { assetType, identifier: usedId } = asset;

    if (assetType === EVM_TOKEN) {
      const location = asset.evmChain ?? undefined;
      if (isEvmIdentifier(usedId)) {
        return {
          address: getAddressFromEvmIdentifier(usedId),
          location,
        };
      }

      if (isEvmIdentifierWithNftId(usedId)) {
        const nftDetail = getNftAssetIdDetail(usedId);
        if (!nftDetail) {
          return undefined;
        }
        return {
          address: nftDetail.contractAddress,
          location,
          nftId: nftDetail.nftId,
        };
      }
    }

    if (isSolanaTokenIdentifier(usedId) && assetType === SOLANA_TOKEN) {
      return {
        address: getAddressFromSolanaIdentifier(usedId),
        location: SOLANA_CHAIN,
      };
    }

    return undefined;
  };

  const useAssetContractInfo: AssetContractInfoReturn = (
    identifier: MaybeRefOrGetter<string | undefined>,
    options?: MaybeRefOrGetter<AssetResolutionOptions>,
  ): ComputedRef<AssetContractInfo | undefined> =>
    computed<AssetContractInfo | undefined>(() => getAssetContractInfo(toValue(identifier), toValue(options)));

  const getTokenAddress = (
    identifier: string,
    options?: AssetResolutionOptions,
  ): string => getAssetContractInfo(identifier, options)?.address || '';

  const useTokenAddress = (
    identifier: MaybeRefOrGetter<string>,
    options?: MaybeRefOrGetter<AssetResolutionOptions>,
  ): ComputedRef<string> =>
    computed<string>(() => getTokenAddress(toValue(identifier), toValue(options)));

  const fetchTokenDetails = async (payload: EvmChainAddress): Promise<ERC20Token> => {
    const outcome = await runTask<ERC20Token, TaskMeta>(
      async () => erc20details(payload),
      { type: TaskType.ERC20_DETAILS, meta: { title: t('actions.assets.erc20.task.title', payload) } },
    );

    if (outcome.success) {
      return outcome.result;
    }
    else if (isActionableFailure(outcome)) {
      notifyError(t('actions.assets.erc20.error.title', payload), t('actions.assets.erc20.error.description', {
        message: outcome.message,
      }));
    }
    return {};
  };

  const assetSearch = async (params: AssetSearchParams): Promise<AssetsWithId> => {
    try {
      const evmChain = params.evmChain && getChain(params.evmChain) ? params.evmChain : undefined;
      return await assetSearchCaller({ ...params, evmChain });
    }
    catch (error: unknown) {
      if (isAbortError(error))
        return [];

      notify({
        display: true,
        group: NotificationGroup.ASSET_SEARCH_ERROR,
        message: t('asset_search.error.message', {
          message: getErrorMessage(error),
        }),
        severity: Severity.ERROR,
        title: t('asset_search.error.title'),
      });
      return [];
    }
  };

  return {
    assetSearch,
    fetchTokenDetails,
    getAssetContractInfo,
    getAssetField,
    getAssetInfo,
    getTokenAddress,
    refetchAssetInfo: queueIdentifier,
    useAssetContractInfo,
    useAssetField,
    useAssetInfo,
    useTokenAddress,
  };
}
