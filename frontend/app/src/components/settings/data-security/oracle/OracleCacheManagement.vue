<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { PriceOracle } from '@/types/settings/price-oracle';
import { CRYPTOCOMPARE_PRIO_LIST_ITEM } from '@/types/settings/prioritized-list-id';
import { TaskType } from '@/types/task-type';
import type {
  DataTableColumn,
  DataTableSortData,
} from '@rotki/ui-library-compat';
import type { PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import type { OracleCacheMeta } from '@/types/prices';

const { t } = useI18n();

const sort: Ref<DataTableSortData> = ref([]);

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('oracle_cache_management.headers.from').toString(),
    key: 'fromAsset',
    sortable: true,
  },
  {
    label: t('oracle_cache_management.headers.to').toString(),
    key: 'toAsset',
    sortable: true,
  },
  {
    label: t('oracle_cache_management.headers.from_date').toString(),
    key: 'fromTimestamp',
    sortable: true,
  },
  {
    label: t('oracle_cache_management.headers.to_date').toString(),
    key: 'toTimestamp',
    sortable: true,
  },
  {
    label: '',
    key: 'actions',
  },
]);

const { isTaskRunning } = useTaskStore();
const { createOracleCache, getPriceCache, deletePriceCache }
  = useBalancePricesStore();

const oracles: PrioritizedListItemData[] = [CRYPTOCOMPARE_PRIO_LIST_ITEM];

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

const filteredData = computed<OracleCacheMeta[]>(() => {
  const from = get(fromAsset);
  const to = get(toAsset);

  return get(cacheData).filter((item) => {
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

const pending = isTaskRunning(TaskType.CREATE_PRICE_CACHE);

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
    const title = t('oracle_cache_management.notification.title').toString();

    const message = t('oracle_cache_management.clear_error', {
      fromAsset: get(assetSymbol(fromAsset)),
      toAsset: get(assetSymbol(toAsset)),
      error: error.message,
    }).toString();

    notify({
      title,
      message,
      severity: Severity.ERROR,
      display: true,
    });
  }
}

async function fetchPrices() {
  const fromAssetVal = get(fromAsset);
  const toAssetVal = get(toAsset);
  const source = get(selection);

  const status = await createOracleCache({
    purgeOld: false,
    fromAsset: fromAssetVal,
    toAsset: toAssetVal,
    source,
  });

  if (!('message' in status))
    await load();

  const from = get(assetSymbol(fromAssetVal));
  const to = get(assetSymbol(toAssetVal));
  const message = status.success
    ? t('oracle_cache_management.notification.success', {
      fromAsset: from,
      toAsset: to,
      source,
    })
    : t('oracle_cache_management.notification.error', {
      fromAsset: from,
      toAsset: to,
      source,
      error: status.message,
    });
  const title = t('oracle_cache_management.notification.title').toString();

  notify({
    title,
    message: message.toString(),
    severity: status.success ? Severity.INFO : Severity.ERROR,
    display: true,
  });
}

function clearFilter() {
  set(fromAsset, '');
  set(toAsset, '');
}

const { show } = useConfirmStore();

function showDeleteConfirmation(entry: OracleCacheMeta) {
  const deleteFromAsset = entry?.fromAsset
    ? get(assetSymbol(entry.fromAsset))
    : '';
  const deleteToAsset = entry?.toAsset ? get(assetSymbol(entry.toAsset)) : '';

  show(
    {
      title: t('oracle_cache_management.delete_confirmation.title'),
      message: t('oracle_cache_management.delete_confirmation.message', {
        selection: get(selection),
        fromAsset: deleteFromAsset,
        toAsset: deleteToAsset,
      }).toString(),
    },
    () => clearCache(entry),
  );
}
</script>

<template>
  <RuiCard class="mt-8">
    <template #header>
      {{ t('oracle_cache_management.title') }}
    </template>
    <template #subheader>
      {{ t('oracle_cache_management.subtitle') }}
    </template>
    <VAutocomplete
      v-model="selection"
      :label="t('oracle_cache_management.select_oracle')"
      prepend-inner-icon="mdi-magnify"
      outlined
      :items="oracles"
      item-value="identifier"
      item-text="identifier"
    >
      <template #selection="{ item }">
        <PrioritizedListEntry :data="item" />
      </template>
      <template #item="{ item }">
        <PrioritizedListEntry :data="item" />
      </template>
    </VAutocomplete>
    <div class="pb-8">
      <div class="flex items-start gap-4">
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
          <RuiIcon name="close-line" />
        </RuiButton>
      </div>
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            :loading="pending"
            color="primary"
            :disabled="!fromAsset || !toAsset || pending"
            size="lg"
            @click="fetchPrices()"
          >
            <template #prepend>
              <RuiIcon name="add-line" />
            </template>
            {{ t('oracle_cache_management.create_cache') }}
          </RuiButton>
        </template>
        <span>{{ t('oracle_cache_management.create_tooltip') }}</span>
      </RuiTooltip>
    </div>
    <RuiDataTable
      outlined
      dense
      :cols="headers"
      :loading="loading"
      :rows="filteredData"
      row-attr="id"
      :sort.sync="sort"
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
                name="delete-bin-line"
              />
            </RuiButton>
          </template>
          <span>{{ t('oracle_cache_management.delete_tooltip') }}</span>
        </RuiTooltip>
      </template>
    </RuiDataTable>

    <OraclePenaltySettings />
  </RuiCard>
</template>
