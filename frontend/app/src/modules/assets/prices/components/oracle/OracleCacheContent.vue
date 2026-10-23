<script setup lang="ts">
import type { OracleCacheMeta } from '@/modules/assets/prices/price-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { NotificationKind, Severity } from '@rotki/common';
import OracleCacheFilter from '@/modules/assets/prices/components/oracle/OracleCacheFilter.vue';
import OracleCacheFormDialog from '@/modules/assets/prices/components/oracle/OracleCacheFormDialog.vue';
import OracleCacheTable from '@/modules/assets/prices/components/oracle/OracleCacheTable.vue';
import { oracleCacheActivity } from '@/modules/assets/prices/prices.activity';
import { OracleCacheFilterKeys } from '@/modules/assets/prices/use-oracle-cache-fields';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { fromRequest, isRequestFailure } from '@/modules/core/api/request-result';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import TableFrame from '@/modules/core/table/TableFrame.vue';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useSetting } from '@/modules/settings/use-setting';
import HintMenuIcon from '@/modules/shell/components/HintMenuIcon.vue';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** The add form's state, opened from the page header's add button. */
const addOpen = defineModel<boolean>('addOpen', { default: false, required: false });

defineSlots<{
  /** the page's tab switch, at the start of the toolbar */
  tabs?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useIsActive } = useTaskCenter();
const { createOracleCache } = usePriceTaskManager();
const { deletePriceCache, getPriceCache } = usePriceApi();
const { getAssetField } = useAssetInfoRetrieval();
const { notify } = useNotificationDispatcher();
const { show } = useConfirmStore();
const cachePending = useIsActive(oracleCacheActivity.kind, ...oracleCacheActivity.partsOf());

const currencySymbol = useSetting('currencySymbol');

const cacheSource = ref<PriceOracle>(PriceOracle.CRYPTOCOMPARE);
const newFromAsset = ref<string>('');
const newToAsset = ref<string>(get(currencySymbol));
/**
 * The bar owns the filter bag; the two assets are read out of it.
 *
 * A ref rather than a writable computed over two string refs: a pill exists before it has a value,
 * and rebuilding the bag from the two keys drops that pending state.
 */
const matches = ref<MatchedKeywordWithBehaviour<string>>({});

const filterFromAsset = computed<string>(() => pickedAsset(OracleCacheFilterKeys.FROM_ASSET));
const filterToAsset = computed<string>(() => pickedAsset(OracleCacheFilterKeys.TO_ASSET));

function pickedAsset(key: string): string {
  const value = get(matches)[key];
  return typeof value === 'string' ? value : '';
}
const cacheEntries = ref<OracleCacheMeta[]>([]);
const loadingCaches = ref<boolean>(false);
/** why the last listing failed, shown by the table in place of its empty text */
const cacheError = shallowRef<unknown>();

const cacheSourceOptions = computed<{ identifier: PriceOracle; label: string }[]>(() => [
  { identifier: PriceOracle.CRYPTOCOMPARE, label: t('oracle_prices.sources.cryptocompare') },
]);

const rows = computed<(OracleCacheMeta & { id: number })[]>(() => {
  const from = get(filterFromAsset);
  const to = get(filterToAsset);

  return get(cacheEntries)
    .filter(entry => (!from || entry.fromAsset === from) && (!to || entry.toAsset === to))
    .map((entry, index) => ({ ...entry, id: index + 1 }));
});

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
  const outcome = await fromRequest(async () => getPriceCache(get(cacheSource)));
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

watch(cacheSource, async () => {
  await loadCaches();
});

async function populateCache(): Promise<void> {
  const outcome = await createOracleCache({
    fromAsset: get(newFromAsset),
    purgeOld: false,
    source: get(cacheSource),
    toAsset: get(newToAsset),
  });

  if (outcome.ok) {
    set(addOpen, false);
    set(newFromAsset, '');
    await loadCaches();
  }
}

async function clearCache(entry: OracleCacheMeta): Promise<void> {
  const source = get(cacheSource);
  try {
    await deletePriceCache(source, entry.fromAsset, entry.toAsset);
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

function showDeleteConfirmation(entry: OracleCacheMeta): void {
  show(
    {
      message: t('oracle_prices.cache.delete.message', {
        fromAsset: getAssetField(entry.fromAsset, 'symbol'),
        source: get(cacheSource),
        toAsset: getAssetField(entry.toAsset, 'symbol'),
      }),
      title: t('oracle_prices.cache.delete.title'),
    },
    async () => clearCache(entry),
  );
}

function clearFilter(): void {
  set(matches, {});
}

onMounted(async () => {
  await loadCaches();
});

defineExpose({
  clearCache,
  clearFilter,
  filterFromAsset,
  filterToAsset,
  loadCaches,
  // with loadCaches, for the page header's refresh button
  loadingCaches,
  matches,
  newFromAsset,
  newToAsset,
  populateCache,
  rows,
});
</script>

<template>
  <TableFrame>
    <template #toolbar>
      <slot name="tabs" />
      <HintMenuIcon>
        {{ t('oracle_prices.cache.hint') }}
      </HintMenuIcon>
      <OracleCacheFilter
        v-model:matches="matches"
        class="flex-1 min-w-48 md:min-w-96"
        :disabled="loadingCaches"
      />
    </template>

    <OracleCacheTable
      :rows="rows"
      :error="cacheError"
      :loading="loadingCaches"
      :disabled="cachePending"
      @delete="showDeleteConfirmation($event)"
    />

    <OracleCacheFormDialog
      v-model:open="addOpen"
      v-model:source="cacheSource"
      v-model:from-asset="newFromAsset"
      v-model:to-asset="newToAsset"
      :loading="cachePending"
      :source-options="cacheSourceOptions"
      @confirm="populateCache()"
    />
  </TableFrame>
</template>
