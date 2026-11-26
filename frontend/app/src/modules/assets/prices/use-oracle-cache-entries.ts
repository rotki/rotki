import type { OracleCacheMeta } from '@/modules/assets/prices/price-types';
import type { PriceOracle } from '@/modules/settings/types/price-oracle';
import type { RowDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { NotificationKind, Severity } from '@rotki/common';
import { set } from '@vueuse/shared';
import { type DeepReadonly, type MaybeRefOrGetter, readonly, type Ref, ref, shallowRef, toValue, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { fromRequest, isRequestFailure } from '@/modules/core/api/request-result';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';

interface UseOracleCacheEntriesReturn {
  /** the caches the source listed last */
  cacheEntries: Readonly<Ref<DeepReadonly<OracleCacheMeta[]>>>;
  /** why the last listing failed, shown by the table in place of its empty text */
  cacheError: Readonly<Ref<unknown>>;
  /** Deletes one cache and lists the caches again; a failure files an error notification. */
  clearCache: (entry: OracleCacheMeta) => Promise<void>;
  /** What a cache row's delete button asks before the row is cleared. */
  deleteConfirm: (entry: OracleCacheMeta) => RowDeleteQuestion;
  /** Lists the caches of the source; only the latest of overlapping listings writes its outcome. */
  loadCaches: () => Promise<void>;
  /** whether a listing is running */
  loadingCaches: Readonly<Ref<boolean>>;
}

/**
 * Holds the price caches one oracle has, listing them again whenever the source changes.
 *
 * @param source - the oracle whose caches are listed and cleared
 */
export function useOracleCacheEntries(source: MaybeRefOrGetter<PriceOracle>): UseOracleCacheEntriesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { deletePriceCache, getPriceCache } = usePriceApi();
  const { getAssetField } = useAssetInfoRetrieval();
  const { notify } = useNotificationDispatcher();

  const cacheEntries = ref<OracleCacheMeta[]>([]);
  const loadingCaches = shallowRef<boolean>(false);
  const cacheError = shallowRef<unknown>();

  /** counts the listings started, so only the latest one writes its outcome */
  let cacheLoads = 0;

  /**
   * Lists the caches of the selected source.
   *
   * @remarks
   * A refresh, a delete or a new cache can start a listing while one is still running. Only the latest
   * one writes the rows, the failure and the loading flag, so an older response that arrives last does
   * not overwrite a newer one.
   */
  async function loadCaches(): Promise<void> {
    const load = ++cacheLoads;
    set(loadingCaches, true);
    set(cacheError, undefined);
    const outcome = await fromRequest(async () => getPriceCache(toValue(source)));
    if (load !== cacheLoads)
      return;
    set(loadingCaches, false);
    if (outcome.ok) {
      set(cacheEntries, outcome.value);
      return;
    }
    set(cacheEntries, []);
    if (isRequestFailure(outcome.error))
      set(cacheError, outcome.error);
  }

  watch(() => toValue(source), async () => {
    await loadCaches();
  });

  async function clearCache(entry: OracleCacheMeta): Promise<void> {
    const oracle = toValue(source);
    try {
      await deletePriceCache(oracle, entry.fromAsset, entry.toAsset);
      await loadCaches();
    }
    catch (error: unknown) {
      notify({
        message: t('oracle_prices.cache.delete.error', {
          error: getErrorMessage(error),
          fromAsset: getAssetField(entry.fromAsset, 'symbol'),
          toAsset: getAssetField(entry.toAsset, 'symbol'),
        }),
        kind: NotificationKind.RESULT,
        severity: Severity.ERROR,
        title: t('oracle_prices.cache.notification.title'),
      });
    }
  }

  function deleteConfirm(entry: OracleCacheMeta): RowDeleteQuestion {
    return {
      message: t('oracle_prices.cache.delete.message', {
        fromAsset: getAssetField(entry.fromAsset, 'symbol'),
        source: toValue(source),
        toAsset: getAssetField(entry.toAsset, 'symbol'),
      }),
      title: t('oracle_prices.cache.delete.title'),
    };
  }

  return {
    cacheEntries: readonly(cacheEntries),
    cacheError: readonly(cacheError),
    clearCache,
    deleteConfirm,
    loadCaches,
    loadingCaches: readonly(loadingCaches),
  };
}
