<script setup lang="ts">
import type { OracleCacheMeta } from '@/types/prices';
import type { PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import PrioritizedListEntry from '@/components/helper/PrioritizedListEntry.vue';
import AssetSelect from '@/components/inputs/AssetSelect.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { PriceOracle } from '@/types/settings/price-oracle';
import { CRYPTOCOMPARE_PRIO_LIST_ITEM } from '@/types/settings/prioritized-list-id';
import { TaskType } from '@/types/task-type';
import { Severity } from '@rotki/common';

type OracleCacheEntry = OracleCacheMeta & { id: number };

const { t } = useI18n();

const sort = ref<DataTableSortData<OracleCacheEntry>>([]);

const columns = computed<DataTableColumn<OracleCacheEntry>[]>(() => [
  {
    key: 'fromAsset',
    label: t('oracle_cache_management.headers.from'),
    sortable: true,
  },
  {
    key: 'toAsset',
    label: t('oracle_cache_management.headers.to'),
    sortable: true,
  },
  {
    key: 'fromTimestamp',
    label: t('oracle_cache_management.headers.from_date'),
    sortable: true,
  },
  {
    key: 'toTimestamp',
    label: t('oracle_cache_management.headers.to_date'),
    sortable: true,
  },
  {
    key: 'actions',
    label: '',
  },
]);

const { useIsTaskRunning } = useTaskStore();
const { createOracleCache, deletePriceCache, getPriceCache } = useBalancePricesStore();

const oracles: PrioritizedListItemData<PriceOracle>[] = [CRYPTOCOMPARE_PRIO_LIST_ITEM];

const loading = ref<boolean>(false);
const confirmClear = ref<boolean>(false);
const cacheData = ref<OracleCacheMeta[]>([]);
const fromAsset = ref<string>('');
const toAsset = ref<string>('');
const selection = ref<PriceOracle>(PriceOracle.CRYPTOCOMPARE);

async function load() {
  set(loading, true);
  set(cacheData, await getPriceCache(PriceOracle.CRYPTOCOMPARE));
  set(loading, false);
}

const rows = computed<OracleCacheEntry[]>(() => {
  const from = get(fromAsset);
  const to = get(toAsset);

  return get(cacheData)
    .map((row, index) => ({
      id: index + 1,
      ...row,
    }))
    .filter((item) => {
      const fromAssetMatch = !from || from === item.fromAsset;
      const toAssetMatch = !to || to === item.toAsset;
      return fromAssetMatch && toAssetMatch;
    });
});

onMounted(async () => {
  await load();
});

watch(selection, async () => {
  await load();
});

const pending = useIsTaskRunning(TaskType.CREATE_PRICE_CACHE);

const { notify } = useNotificationsStore();
const { assetSymbol } = useAssetInfoRetrieval();

async function clearCache(entry: OracleCacheMeta) {
  const { fromAsset, toAsset } = entry;
  set(confirmClear, false);
  try {
    await deletePriceCache(get(selection), fromAsset, toAsset);
    await load();
  }
  catch (error: any) {
    const title = t('oracle_cache_management.notification.title');

    const message = t('oracle_cache_management.clear_error', {
      error: error.message,
      fromAsset: get(assetSymbol(fromAsset)),
      toAsset: get(assetSymbol(toAsset)),
    });

    notify({
      display: true,
      message,
      severity: Severity.ERROR,
      title,
    });
  }
}

async function fetchPrices() {
  const fromAssetVal = get(fromAsset);
  const toAssetVal = get(toAsset);
  const source = get(selection);

  const status = await createOracleCache({
    fromAsset: fromAssetVal,
    purgeOld: false,
    source,
    toAsset: toAssetVal,
  });

  if (!('message' in status))
    await load();

  const from = get(assetSymbol(fromAssetVal));
  const to = get(assetSymbol(toAssetVal));
  const message = status.success
    ? t('oracle_cache_management.notification.success', {
        fromAsset: from,
        source,
        toAsset: to,
      })
    : t('oracle_cache_management.notification.error', {
        error: status.message,
        fromAsset: from,
        source,
        toAsset: to,
      });
  const title = t('oracle_cache_management.notification.title');

  notify({
    display: true,
    message: message.toString(),
    severity: status.success ? Severity.INFO : Severity.ERROR,
    title,
  });
}

function clearFilter() {
  set(fromAsset, '');
  set(toAsset, '');
}

const { show } = useConfirmStore();

function showDeleteConfirmation(entry: OracleCacheMeta) {
  const deleteFromAsset = entry?.fromAsset ? get(assetSymbol(entry.fromAsset)) : '';
  const deleteToAsset = entry?.toAsset ? get(assetSymbol(entry.toAsset)) : '';

  show(
    {
      message: t('oracle_cache_management.delete_confirmation.message', {
        fromAsset: deleteFromAsset,
        selection: get(selection),
        toAsset: deleteToAsset,
      }),
      title: t('oracle_cache_management.delete_confirmation.title'),
    },
    () => clearCache(entry),
  );
}
</script>

<template>
  <div>
    <div class="pt-5 pb-8 border-t border-default flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('oracle_cache_management.title') }}
        </template>
        <template #subtitle>
          {{ t('oracle_cache_management.subtitle') }}
        </template>
      </SettingCategoryHeader>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            :loading="pending"
            color="primary"
            :disabled="!fromAsset || !toAsset || pending"
            @click="fetchPrices()"
          >
            <template #prepend>
              <RuiIcon
                name="lu-plus"
                size="16"
              />
            </template>
            {{ t('oracle_cache_management.create_cache') }}
          </RuiButton>
        </template>
        <span>{{ t('oracle_cache_management.create_tooltip') }}</span>
      </RuiTooltip>
    </div>
    <div>
      <RuiAutoComplete
        v-model="selection"
        :label="t('oracle_cache_management.select_oracle')"
        variant="outlined"
        :options="oracles"
        :item-height="60"
        key-attr="identifier"
      >
        <template #selection="{ item }">
          <PrioritizedListEntry :data="item" />
        </template>
        <template #item="{ item }">
          <PrioritizedListEntry :data="item" />
        </template>
      </RuiAutoComplete>
      <div class="flex items-start gap-4 pb-4">
        <AssetSelect
          v-model="fromAsset"
          clearable
          :disabled="pending"
          outlined
          :label="t('oracle_cache_management.from_asset')"
        />
        <AssetSelect
          v-model="toAsset"
          clearable
          :disabled="pending"
          outlined
          :label="t('oracle_cache_management.to_asset')"
        />
        <RuiButton
          class="mt-1"
          variant="text"
          icon
          large
          @click="clearFilter()"
        >
          <RuiIcon name="lu-x" />
        </RuiButton>
      </div>
      <RuiDataTable
        v-model:sort="sort"
        outlined
        dense
        :cols="columns"
        :loading="loading"
        :rows="rows"
        row-attr="id"
        class="bg-white dark:bg-transparent"
      >
        <template #item.fromAsset="{ row }">
          <AssetDetails
            opens-details
            :asset="row.fromAsset"
          />
        </template>
        <template #item.toAsset="{ row }">
          <AssetDetails
            opens-details
            :asset="row.toAsset"
          />
        </template>
        <template #item.toTimestamp="{ row }">
          <DateDisplay :timestamp="row.toTimestamp" />
        </template>
        <template #item.fromTimestamp="{ row }">
          <DateDisplay :timestamp="row.fromTimestamp" />
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
                @click="showDeleteConfirmation(row)"
              >
                <RuiIcon
                  size="16"
                  name="lu-trash-2"
                />
              </RuiButton>
            </template>
            <span>{{ t('oracle_cache_management.delete_tooltip') }}</span>
          </RuiTooltip>
        </template>
      </RuiDataTable>
    </div>
  </div>
</template>
