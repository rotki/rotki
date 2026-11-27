import { watchImmediate } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type DeepReadonly, type MaybeRefOrGetter, readonly, type Ref, shallowRef, toValue, watch } from 'vue';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

interface UseAccountAssetsReturn {
  /** Every asset the account has held at any time, as identifiers. */
  assets: ComputedRef<string[]>;
  loading: DeepReadonly<Ref<boolean>>;
  error: DeepReadonly<Ref<string | undefined>>;
  /** The account has events not replayed into balances yet, so the list may be missing assets. */
  processingRequired: DeepReadonly<Ref<boolean>>;
}

/**
 * Lists the assets an account has ever held, for the asset picker.
 *
 * @remarks
 * Ever held, not held now: an asset the account has since emptied still has a history to show.
 * Reloads with the account, after a history sync and after the backend finishes processing, since
 * either can add an asset. A load that finishes after a newer one started is dropped.
 */
export function useAccountAssets(account: MaybeRefOrGetter<string | undefined>): UseAccountAssetsReturn {
  const loaded = shallowRef<string[]>([]);
  const loading = shallowRef<boolean>(false);
  const error = shallowRef<string>();
  const processingRequired = shallowRef<boolean>(false);

  const { historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { fetchHistoricalBalanceAssets } = useHistoricalBalancesApi();
  const { syncCompleted } = useSyncCompleted();

  let latestRequest = 0;

  async function refresh(): Promise<void> {
    const request = ++latestRequest;
    const locationLabel = toValue(account);
    set(error, undefined);
    if (!locationLabel) {
      set(loaded, []);
      set(processingRequired, false);
      set(loading, false);
      return;
    }

    set(loading, true);
    try {
      const response = await fetchHistoricalBalanceAssets({ locationLabel });
      if (request !== latestRequest)
        return;
      set(loaded, response.entries);
      set(processingRequired, response.processingRequired);
    }
    catch (error_: unknown) {
      if (request !== latestRequest)
        return;
      logger.error(error_);
      set(loaded, []);
      set(processingRequired, false);
      set(error, getErrorMessage(error_));
    }
    finally {
      if (request === latestRequest)
        set(loading, false);
    }
  }

  watchImmediate(() => toValue(account), refresh);
  watch(syncCompleted, refresh);
  watch(historicalBalanceProcessingCompleted, refresh);

  return {
    assets: computed<string[]>(() => get(loaded)),
    error: readonly(error),
    loading: readonly(loading),
    processingRequired: readonly(processingRequired),
  };
}
