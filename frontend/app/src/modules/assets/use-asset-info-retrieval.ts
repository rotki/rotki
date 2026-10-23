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
} from '@rotki/common';
import { startPromise } from '@shared/utils';
import { err, isErr, type Result } from 'plainfp/result';
import { type AssetSearchParams, useAssetInfoApi } from '@/modules/assets/api/use-asset-info-api';
import { erc20InfoActivity } from '@/modules/assets/assets.activity';
import { type AssetsWithId, EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_CHAIN, SOLANA_TOKEN } from '@/modules/assets/types';
import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { processAssetInfo, useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { isAbortError } from '@/modules/core/common/helpers/is-of-enum';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isActionable, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { activityLabelOf } from '@/modules/task-center/activity-labels';
import { type RunBackendTask, type TaskOutcome, useNativeTask } from '@/modules/task-center/use-native-task';

export interface AssetResolutionOptions {
  associate?: boolean;
  collectionParent?: boolean;
}

export const NO_COLLECTION_RESOLVE: AssetResolutionOptions = { collectionParent: false } as const;

/**
 * Upper bound for the ERC20 token detail lookup. The backend queries live RPC nodes, which
 * can stall under rate limiting; past this we give up, abort the backend task and let the user
 * type the token information manually.
 */
const ERC20_DETAILS_TIMEOUT_MS = 15_000;

/** How long a lookup may wait queued before it starts, after which it is cancelled. */
const ERC20_QUEUED_TIMEOUT_MS = 2 * ERC20_DETAILS_TIMEOUT_MS;

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
  refetchAssetInfo: (key: string) => void;
  useAssetContractInfo: AssetContractInfoReturn;
  useAssetField: (identifier: MaybeRefOrGetter<string | undefined>, field: AssetStringField, options?: MaybeRefOrGetter<AssetResolutionOptions>) => ComputedRef<string>;
  useAssetInfo: AssetInfoReturn;
}

export function useAssetInfoRetrieval(): UseAssetInfoRetrievalReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { assetSearch: assetSearchCaller, erc20details } = useAssetInfoApi();
  const { fetchedAssetCollections, queueIdentifier, resolve: resolveAsset } = useAssetInfoCache();
  const { cancelActivity, submitTask } = useNativeTask();
  const { cancelTaskById } = useTaskHandler();

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

  /**
   * The body of a token details read: fails, with a hint to enter the details by hand, when the
   * backend takes longer than {@link ERC20_DETAILS_TIMEOUT_MS}, and aborts the backend task then.
   */
  const readTokenDetails = async (runTask: RunBackendTask, payload: EvmChainAddress): Promise<Result<ERC20Token, TaskError>> => {
    const timedOut = Symbol('timed-out');
    let backendTaskId: number | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<typeof timedOut>((resolve) => {
      // eslint-disable-next-line @rotki/composable-require-cleanup -- cleared in the finally block below, so it never outlives this call
      timer = setTimeout(resolve, ERC20_DETAILS_TIMEOUT_MS, timedOut);
    });

    try {
      const outcome = await Promise.race([
        runTask<ERC20Token>(async () => {
          const pending = await erc20details(payload);
          backendTaskId = pending.taskId;
          return pending;
        }),
        timeout,
      ]);
      if (outcome !== timedOut)
        return outcome;

      if (backendTaskId !== undefined)
        startPromise(cancelTaskById(backendTaskId));
      return err(TaskFailed({ message: t('actions.assets.erc20.error.timeout') }));
    }
    finally {
      clearTimeout(timer);
    }
  };

  /**
   * Reads a token's details as a task.
   *
   * @remarks
   * A failure, a slow backend included, is reported only by the task's row. A read still queued
   * after {@link ERC20_QUEUED_TIMEOUT_MS} is cancelled, so the form never waits on it forever.
   *
   * @returns the details, or empty ones when the task failed or never started
   */
  const fetchTokenDetails = async (payload: EvmChainAddress): Promise<ERC20Token> => {
    const timedOut = Symbol('timed-out');
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<typeof timedOut>((resolve) => {
      // eslint-disable-next-line @rotki/composable-require-cleanup -- cleared in the finally block below, so it never outlives this call
      timer = setTimeout(resolve, ERC20_QUEUED_TIMEOUT_MS, timedOut);
    });

    const task: Promise<TaskOutcome<ERC20Token>> = submitTask<ERC20Token>({
      id: erc20InfoActivity.id(payload),
      kind: erc20InfoActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<ERC20Token, TaskError>> => readTokenDetails(runTask, payload),
      subtitle: activityLabelOf(erc20InfoActivity, { address: payload.address, chain: payload.evmChain }),
      title: t('task_center.group.assets'),
    });

    try {
      const outcome = await Promise.race([task, timeout]);

      if (outcome === timedOut) {
        cancelActivity(erc20InfoActivity.kind, ...erc20InfoActivity.partsOf(payload));
        return {};
      }

      if (!isErr(outcome)) {
        return outcome.value;
      }
      else if (isActionable(outcome.error)) {
        logger.error('Failed to read the token details:', outcome.error.message);
      }
      return {};
    }
    finally {
      if (timer !== undefined)
        clearTimeout(timer);
    }
  };

  /**
   * Searches the assets, with an aborted search reading as no matches.
   *
   * @remarks
   * Any other failure rejects, so the surface that ran the search can say so where the user typed;
   * a notification would report it away from the input.
   */
  const assetSearch = async (params: AssetSearchParams): Promise<AssetsWithId> => {
    try {
      const evmChain = params.evmChain && getChain(params.evmChain) ? params.evmChain : undefined;
      return await assetSearchCaller({ ...params, evmChain });
    }
    catch (error: unknown) {
      if (isAbortError(error))
        return [];
      throw error;
    }
  };

  return {
    assetSearch,
    fetchTokenDetails,
    getAssetContractInfo,
    getAssetField,
    getAssetInfo,
    refetchAssetInfo: queueIdentifier,
    useAssetContractInfo,
    useAssetField,
    useAssetInfo,
  };
}
