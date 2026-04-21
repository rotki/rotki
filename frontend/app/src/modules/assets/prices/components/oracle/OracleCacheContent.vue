<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { OracleCacheMeta } from '@/modules/assets/prices/price-types';
import { Severity } from '@rotki/common';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import AssetSelect from '@/modules/shell/components/inputs/AssetSelect.vue';

const { t } = useI18n({ useScope: 'global' });

const { useIsTaskRunning } = useTaskStore();
const { createOracleCache } = usePriceTaskManager();
const { deletePriceCache, getPriceCache } = usePriceApi();
const { getAssetField } = useAssetInfoRetrieval();
const { notify } = useNotificationDispatcher();
const { show } = useConfirmStore();
const cachePending = useIsTaskRunning(TaskType.CREATE_PRICE_CACHE);

const cacheSource = ref<PriceOracle>(PriceOracle.CRYPTOCOMPARE);
const newFromAsset = ref<string>('');
const newToAsset = ref<string>('');
const filterFromAsset = ref<string>('');
const filterToAsset = ref<string>('');
const cacheEntries = ref<OracleCacheMeta[]>([]);
const loadingCaches = ref<boolean>(false);

const cacheSourceOptions = computed<{ identifier: PriceOracle; label: string }[]>(() => [
  { identifier: PriceOracle.CRYPTOCOMPARE, label: t('oracle_prices.sources.cryptocompare') },
]);

const columns = computed<DataTableColumn<OracleCacheMeta & { id: number }>[]>(() => [
  {
    key: 'fromAsset',
    label: t('oracle_prices.cache.headers.from_asset'),
  },
  {
    key: 'toAsset',
    label: t('oracle_prices.cache.headers.to_asset'),
  },
  {
    key: 'fromTimestamp',
    label: t('oracle_prices.cache.headers.from_date'),
  },
  {
    key: 'toTimestamp',
    label: t('oracle_prices.cache.headers.to_date'),
  },
  {
    class: 'w-[3rem]',
    key: 'actions',
    label: '',
  },
]);

const rows = computed<(OracleCacheMeta & { id: number })[]>(() => {
  const from = get(filterFromAsset);
  const to = get(filterToAsset);

  return get(cacheEntries)
    .filter(entry => (!from || entry.fromAsset === from) && (!to || entry.toAsset === to))
    .map((entry, index) => ({ ...entry, id: index + 1 }));
});

async function loadCaches(): Promise<void> {
  set(loadingCaches, true);
  try {
    set(cacheEntries, await getPriceCache(get(cacheSource)));
  }
  catch (error: unknown) {
    notify({
      display: true,
      message: getErrorMessage(error),
      severity: Severity.ERROR,
      title: t('oracle_prices.cache.notification.title'),
    });
    set(cacheEntries, []);
  }
  finally {
    set(loadingCaches, false);
  }
}

watch(cacheSource, async () => {
  await loadCaches();
});

async function populateCache(): Promise<void> {
  const source = get(cacheSource);
  const fromAssetVal = get(newFromAsset);
  const toAssetVal = get(newToAsset);

  const status = await createOracleCache({
    fromAsset: fromAssetVal,
    purgeOld: false,
    source,
    toAsset: toAssetVal,
  });

  if (!('message' in status))
    await loadCaches();

  const from = getAssetField(fromAssetVal, 'symbol');
  const to = getAssetField(toAssetVal, 'symbol');

  const message = status.success
    ? t('oracle_prices.cache.notification.success', {
        fromAsset: from,
        source,
        toAsset: to,
      })
    : t('oracle_prices.cache.notification.error', {
        error: status.message,
        fromAsset: from,
        source,
        toAsset: to,
      });

  notify({
    display: true,
    message: message.toString(),
    severity: status.success ? Severity.INFO : Severity.ERROR,
    title: t('oracle_prices.cache.notification.title'),
  });
}

async function clearCache(entry: OracleCacheMeta): Promise<void> {
  const source = get(cacheSource);
  try {
    await deletePriceCache(source, entry.fromAsset, entry.toAsset);
    await loadCaches();
  }
  catch (error: unknown) {
    notify({
      display: true,
      message: t('oracle_prices.cache.delete.error', {
        error: getErrorMessage(error),
        fromAsset: getAssetField(entry.fromAsset, 'symbol'),
        toAsset: getAssetField(entry.toAsset, 'symbol'),
      }),
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
  set(filterFromAsset, '');
  set(filterToAsset, '');
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
  newFromAsset,
  newToAsset,
  populateCache,
  rows,
});
</script>

<template>
  <div class="flex flex-col gap-6">
    <RuiCard>
      <template #header>
        {{ t('oracle_prices.cache.create.title') }}
      </template>
      <div class="flex flex-col gap-4">
        <RuiAutoComplete
          v-model="cacheSource"
          :label="t('oracle_prices.cache.dialog.source')"
          variant="outlined"
          :options="cacheSourceOptions"
          key-attr="identifier"
          text-attr="label"
          :disabled="cachePending || loadingCaches"
          hide-details
        />
        <div class="flex flex-col sm:flex-row gap-4">
          <AssetSelect
            v-model="newFromAsset"
            class="flex-1"
            :label="t('price_management.from_asset')"
            outlined
            :disabled="cachePending"
          />
          <AssetSelect
            v-model="newToAsset"
            class="flex-1"
            :label="t('price_management.to_asset')"
            outlined
            :disabled="cachePending"
          />
        </div>
        <div class="flex justify-end">
          <RuiButton
            color="primary"
            :loading="cachePending"
            :disabled="!newFromAsset || !newToAsset || cachePending"
            @click="populateCache()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-plus"
                size="16"
              />
            </template>
            {{ t('oracle_prices.cache.dialog.create') }}
          </RuiButton>
        </div>
      </div>
    </RuiCard>

    <RuiCard>
      <template #header>
        {{ t('oracle_prices.cache.dialog.existing_title') }}
      </template>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col sm:flex-row gap-4 items-start">
          <AssetSelect
            v-model="filterFromAsset"
            class="flex-1"
            :label="t('oracle_prices.cache.filter.from_asset')"
            clearable
            outlined
            :disabled="loadingCaches"
          />
          <AssetSelect
            v-model="filterToAsset"
            class="flex-1"
            :label="t('oracle_prices.cache.filter.to_asset')"
            clearable
            outlined
            :disabled="loadingCaches"
          />
          <RuiButton
            class="mt-1"
            variant="text"
            icon
            :disabled="loadingCaches"
            @click="clearFilter()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
        <RuiDataTable
          outlined
          dense
          :cols="columns"
          :loading="loadingCaches"
          :rows="rows"
          row-attr="id"
          :empty="{ label: t('oracle_prices.cache.dialog.empty') }"
        >
          <template #item.fromAsset="{ row }">
            <AssetDetails :asset="row.fromAsset" />
          </template>
          <template #item.toAsset="{ row }">
            <AssetDetails :asset="row.toAsset" />
          </template>
          <template #item.fromTimestamp="{ row }">
            <DateDisplay :timestamp="Number(row.fromTimestamp)" />
          </template>
          <template #item.toTimestamp="{ row }">
            <DateDisplay :timestamp="Number(row.toTimestamp)" />
          </template>
          <template #item.actions="{ row }">
            <RuiTooltip
              :popper="{ placement: 'top' }"
              :open-delay="400"
            >
              <template #activator>
                <RuiButton
                  color="primary"
                  variant="text"
                  icon
                  :disabled="cachePending"
                  @click="showDeleteConfirmation(row)"
                >
                  <RuiIcon
                    size="16"
                    name="lu-trash-2"
                  />
                </RuiButton>
              </template>
              {{ t('oracle_prices.cache.delete.tooltip') }}
            </RuiTooltip>
          </template>
        </RuiDataTable>
      </div>
    </RuiCard>
  </div>
</template>
