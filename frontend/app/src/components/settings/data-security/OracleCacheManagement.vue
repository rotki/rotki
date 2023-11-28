<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { type DataTableHeader } from '@/types/vuetify';
import { PriceOracle } from '@/types/settings/price-oracle';
import { type PrioritizedListItemData } from '@/types/settings/prioritized-list-data';
import { CRYPTOCOMPARE_PRIO_LIST_ITEM } from '@/types/settings/prioritized-list-id';
import { TaskType } from '@/types/task-type';
import { type OracleCacheMeta } from '@/types/prices';

const { t } = useI18n();

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('oracle_cache_management.headers.from').toString(),
    value: 'fromAsset'
  },
  {
    text: t('oracle_cache_management.headers.to').toString(),
    value: 'toAsset'
  },
  {
    text: t('oracle_cache_management.headers.from_date').toString(),
    value: 'fromTimestamp'
  },
  {
    text: t('oracle_cache_management.headers.to_date').toString(),
    value: 'toTimestamp'
  },
  {
    text: '',
    value: 'actions'
  }
]);

const { isTaskRunning } = useTaskStore();
const { createOracleCache, getPriceCache, deletePriceCache } =
  useBalancePricesStore();

const oracles: PrioritizedListItemData[] = [CRYPTOCOMPARE_PRIO_LIST_ITEM];

const loading = ref<boolean>(false);
const confirmClear = ref<boolean>(false);
const cacheData = ref<OracleCacheMeta[]>([]);
const fromAsset = ref<string>('');
const toAsset = ref<string>('');
const selection = ref<PriceOracle>(PriceOracle.CRYPTOCOMPARE);

const load = async () => {
  set(loading, true);
  set(cacheData, await getPriceCache(PriceOracle.CRYPTOCOMPARE));
  set(loading, false);
};

const filteredData = computed<OracleCacheMeta[]>(() => {
  const from = get(fromAsset);
  const to = get(toAsset);

  return get(cacheData).filter(item => {
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

const clearCache = async (entry: OracleCacheMeta) => {
  const { fromAsset, toAsset } = entry;
  set(confirmClear, false);
  try {
    await deletePriceCache(get(selection), fromAsset, toAsset);
    await load();
  } catch (e: any) {
    const title = t('oracle_cache_management.notification.title').toString();

    const message = t('oracle_cache_management.clear_error', {
      fromAsset: get(assetSymbol(fromAsset)),
      toAsset: get(assetSymbol(toAsset)),
      error: e.message
    }).toString();

    notify({
      title,
      message,
      severity: Severity.ERROR,
      display: true
    });
  }
};

const fetchPrices = async () => {
  const fromAssetVal = get(fromAsset);
  const toAssetVal = get(toAsset);
  const source = get(selection);

  const status = await createOracleCache({
    purgeOld: false,
    fromAsset: fromAssetVal,
    toAsset: toAssetVal,
    source
  });

  if (!('message' in status)) {
    await load();
  }

  const from = get(assetSymbol(fromAssetVal));
  const to = get(assetSymbol(toAssetVal));
  const message = status.success
    ? t('oracle_cache_management.notification.success', {
        fromAsset: from,
        toAsset: to,
        source
      })
    : t('oracle_cache_management.notification.error', {
        fromAsset: from,
        toAsset: to,
        source,
        error: status.message
      });
  const title = t('oracle_cache_management.notification.title').toString();

  notify({
    title,
    message: message.toString(),
    severity: status.success ? Severity.INFO : Severity.ERROR,
    display: true
  });
};

const clearFilter = () => {
  set(fromAsset, '');
  set(toAsset, '');
};

const { show } = useConfirmStore();

const showDeleteConfirmation = (entry: OracleCacheMeta) => {
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
        toAsset: deleteToAsset
      }).toString()
    },
    () => clearCache(entry)
  );
};
</script>

<template>
  <VCard class="mt-8">
    <VCardTitle>
      <CardTitle>{{ t('oracle_cache_management.title') }}</CardTitle>
    </VCardTitle>
    <VCardSubtitle>
      {{ t('oracle_cache_management.subtitle') }}
    </VCardSubtitle>
    <VCardText>
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
        <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
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
      <DataTable :headers="headers" :loading="loading" :items="filteredData">
        <template #item.fromAsset="{ item }">
          <AssetDetails opens-details :asset="item.fromAsset" />
        </template>
        <template #item.toAsset="{ item }">
          <AssetDetails opens-details :asset="item.toAsset" />
        </template>
        <template #item.toTimestamp="{ item }">
          <DateDisplay :timestamp="item.toTimestamp" />
        </template>
        <template #item.fromTimestamp="{ item }">
          <DateDisplay :timestamp="item.fromTimestamp" />
        </template>
        <template #item.actions="{ item }">
          <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
            <template #activator>
              <RuiButton
                color="primary"
                variant="text"
                icon
                @click="showDeleteConfirmation(item)"
              >
                <RuiIcon size="16" name="delete-bin-line" />
              </RuiButton>
            </template>
            <span>{{ t('oracle_cache_management.delete_tooltip') }}</span>
          </RuiTooltip>
        </template>
      </DataTable>
    </VCardText>
  </VCard>
</template>
