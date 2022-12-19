<script setup lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import { type DataTableHeader } from 'vuetify';
import DataTable from '@/components/helper/DataTable.vue';
import Fragment from '@/components/helper/Fragment';
import PrioritizedListEntry from '@/components/helper/PrioritizedListEntry.vue';
import { type OracleCacheMeta } from '@/services/balances/types';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useNotificationsStore } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { PriceOracle } from '@/types/price-oracle';
import { type PrioritizedListItemData } from '@/types/prioritized-list-data';
import { CRYPTOCOMPARE_PRIO_LIST_ITEM } from '@/types/prioritized-list-id';
import { TaskType } from '@/types/task-type';
import { useConfirmStore } from '@/store/confirm';

const { t, tc } = useI18n();

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

const { isTaskRunning } = useTasks();
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
      title: tc('oracle_cache_management.delete_confirmation.title'),
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
  <fragment>
    <v-card class="mt-8">
      <v-card-title>
        <card-title>{{ tc('oracle_cache_management.title') }}</card-title>
      </v-card-title>
      <v-card-subtitle>
        {{ tc('oracle_cache_management.subtitle') }}
      </v-card-subtitle>
      <v-card-text>
        <v-autocomplete
          v-model="selection"
          :label="t('oracle_cache_management.select_oracle')"
          prepend-inner-icon="mdi-magnify"
          outlined
          :items="oracles"
          item-value="identifier"
          item-text="identifier"
        >
          <template #selection="{ item }">
            <prioritized-list-entry :data="item" />
          </template>
          <template #item="{ item }">
            <prioritized-list-entry :data="item" />
          </template>
        </v-autocomplete>
        <div class="pb-8">
          <v-row align="center">
            <v-col>
              <asset-select
                v-model="fromAsset"
                clearable
                :disabled="pending"
                outlined
                :label="tc('oracle_cache_management.from_asset')"
              />
            </v-col>
            <v-col>
              <asset-select
                v-model="toAsset"
                clearable
                :disabled="pending"
                outlined
                :label="tc('oracle_cache_management.to_asset')"
              />
            </v-col>
            <v-col cols="auto" class="pb-10 pr-8">
              <v-btn icon large @click="clearFilter">
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </v-col>
          </v-row>
          <v-tooltip open-delay="400" top>
            <template #activator="{ on, attrs }">
              <v-btn
                v-bind="attrs"
                :loading="pending"
                large
                color="primary"
                :disabled="!fromAsset || !toAsset || pending"
                v-on="on"
                @click="fetchPrices()"
              >
                <v-icon class="mr-2">mdi-plus-circle</v-icon>
                {{ t('oracle_cache_management.create_cache') }}
              </v-btn>
            </template>
            <span>{{ t('oracle_cache_management.create_tooltip') }}</span>
          </v-tooltip>
        </div>
        <v-sheet outlined rounded>
          <data-table
            :headers="headers"
            :loading="loading"
            :items="filteredData"
          >
            <template #item.fromAsset="{ item }">
              <asset-details opens-details :asset="item.fromAsset" />
            </template>
            <template #item.toAsset="{ item }">
              <asset-details opens-details :asset="item.toAsset" />
            </template>
            <template #item.toTimestamp="{ item }">
              <date-display :timestamp="item.toTimestamp" />
            </template>
            <template #item.fromTimestamp="{ item }">
              <date-display :timestamp="item.fromTimestamp" />
            </template>
            <template #item.actions="{ item }">
              <v-tooltip open-delay="400" top>
                <template #activator="{ on, attrs }">
                  <v-btn
                    color="primary"
                    v-bind="attrs"
                    icon
                    v-on="on"
                    @click="showDeleteConfirmation(item)"
                  >
                    <v-icon>mdi-delete</v-icon>
                  </v-btn>
                </template>
                <span>{{ t('oracle_cache_management.delete_tooltip') }}</span>
              </v-tooltip>
            </template>
          </data-table>
        </v-sheet>
      </v-card-text>
    </v-card>
  </fragment>
</template>
