import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { ERC20Token } from '@/modules/accounts/blockchain-accounts';
import type { EvmChainAddress } from '@/modules/history/events/event-payloads';
import {
  type AssetInfoWithId,
  getAddressFromEvmIdentifier,
  getAddressFromHyperliquidTokenIdentifier,
  getAddressFromSolanaIdentifier,
  getNftAssetIdDetail,
  isEvmIdentifier,
  isEvmIdentifierWithNftId,
  isHyperliquidTokenIdentifier,
  isSolanaTokenIdentifier,
  NotificationGroup,
  Severity,
} from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { type AssetSearchParams, useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { type AssetsWithId, EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { processAssetInfo, useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { isAbortError } from '@/modules/core/common/helpers/is-of-enum';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { type TaskOutcome, useNativeTask } from '@/modules/task-center/use-native-task';

export interface AssetResolutionOptions {
  associate?: boolean;
  collectionParent?: boolean;
}

export const NO_COLLECTION_RESOLVE: AssetResolutionOptions = { collectionParent: false } as const;

/**
 * Upper bound for the ERC20 token detail lookup. The backend queries live RPC nodes, which
 * can stall under rate limiting; past this we give up, cancel the task and let the user type
 * the token information manually.
 */
const ERC20_DETAILS_TIMEOUT_MS = 15_000;

interface AssetWithResolutionStatus extends AssetInfoWithId {
  resolved: boolean;
}

interface AssetContractInfo {
  address: string;
  location?: string;
  nftId?: string;
}

function getEvmAssetContractInfo(identifier: string, location?: string): AssetContractInfo | undefined {
  if (isEvmIdentifier(identifier)) {
    return {
      address: getAddressFromEvmIdentifier(identifier),
      location,
    };
  }

  if (!isEvmIdentifierWithNftId(identifier))
    return undefined;

  const nftDetail = getNftAssetIdDetail(identifier);
  if (!nftDetail)
    return undefined;

  return {
    address: nftDetail.contractAddress,
    location,
    nftId: nftDetail.nftId,
  };
}

export type AssetStringField = 'symbol' | 'name';

export type PlainAssetInfoReturn = (identifier: string | undefined, options?: AssetResolutionOptions) => AssetWithResolutionStatus | null;

type AssetInfoReturn = (identifier: MaybeRefOrGetter<string | undefined>, options?: MaybeRefOrGetter<AssetResolutionOptions>) => ComputedRef<AssetWithResolutionStatus | null>;

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
  const { cancelActivity, submitTask } = useNativeTask();

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

    const { assetType, evmChain, identifier: usedId } = asset;

    if (assetType === EVM_TOKEN)
      return getEvmAssetContractInfo(usedId, evmChain ?? undefined);

    if (isSolanaTokenIdentifier(usedId) && assetType === SOLANA_TOKEN) {
      return {
        address: getAddressFromSolanaIdentifier(usedId),
        location: SOLANA_CHAIN,
      };
    }

    if (isHyperliquidTokenIdentifier(usedId) && assetType === HYPERLIQUID_TOKEN) {
      return {
        address: getAddressFromHyperliquidTokenIdentifier(usedId),
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
  ): string => getAssetContractInfo(identifier, options)?.address ?? '';

  const useTokenAddress = (
    identifier: MaybeRefOrGetter<string>,
    options?: MaybeRefOrGetter<AssetResolutionOptions>,
  ): ComputedRef<string> =>
    computed<string>(() => getTokenAddress(toValue(identifier), toValue(options)));

  const fetchTokenDetails = async (payload: EvmChainAddress): Promise<ERC20Token> => {
    const timedOut = Symbol('timed-out');
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<typeof timedOut>((resolve) => {
      // Cleared in the finally block below, so it never outlives this call.
      // eslint-disable-next-line @rotki/composable-require-cleanup
      timer = setTimeout(resolve, ERC20_DETAILS_TIMEOUT_MS, timedOut);
    });

    let details: ERC20Token = {};
    const task: Promise<TaskOutcome> = submitTask({
      id: makeActivityId(ActivityKind.ASSETS, ActivityPart.ERC20, payload.evmChain, payload.address),
      kind: ActivityKind.ASSETS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<ERC20Token>(
          async () => erc20details(payload),
        ),
        (result) => {
          details = result;
        },
      ),
      subtitle: activityLabel(ActivityKind.ASSETS, ActivityPart.ERC20, { address: payload.address, chain: payload.evmChain }),
      title: t('task_center.group.assets'),
    });

    try {
      const outcome = await Promise.race([task, timeout]);

      // The lookup can stall when no RPC node answers (e.g. rate limiting). Bail out
      // instead of leaving the caller awaiting indefinitely, and cancel the backend task.
      if (outcome === timedOut) {
        cancelActivity(ActivityKind.ASSETS, ActivityPart.ERC20, payload.evmChain, payload.address);
        notifyError(t('actions.assets.erc20.error.title', payload), t('actions.assets.erc20.error.timeout'));
        return {};
      }

      if (!isErr(outcome)) {
        return details;
      }
      else if (isActionable(outcome.error)) {
        notifyError(t('actions.assets.erc20.error.title', payload), t('actions.assets.erc20.error.description', {
          message: outcome.error.message,
        }));
      }
      return {};
    }
    finally {
      if (timer !== undefined)
        clearTimeout(timer);
    }
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
