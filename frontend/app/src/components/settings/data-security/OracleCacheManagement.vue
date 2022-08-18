<template>
  <fragment>
    <v-card class="mt-8">
      <v-card-title>
        <card-title>{{ $tc('oracle_cache_management.title') }}</card-title>
      </v-card-title>
      <v-card-subtitle>
        {{ $tc('oracle_cache_management.subtitle') }}
      </v-card-subtitle>
      <v-card-text>
        <v-autocomplete
          v-model="selection"
          :label="$t('oracle_cache_management.select_oracle')"
          prepend-inner-icon="mdi-magnify"
          outlined
          :items="oracles"
        >
          <template #selection="{ item }">
            <oracle-entry :identifier="item" />
          </template>
          <template #item="{ item }">
            <oracle-entry :identifier="item" />
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
                :label="$tc('oracle_cache_management.from_asset')"
              />
            </v-col>
            <v-col>
              <asset-select
                v-model="toAsset"
                clearable
                :disabled="pending"
                outlined
                :label="$tc('oracle_cache_management.to_asset')"
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
                {{ $t('oracle_cache_management.create_cache') }}
              </v-btn>
            </template>
            <span>{{ $t('oracle_cache_management.create_tooltip') }}</span>
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
                    @click="confirmDelete(item)"
                  >
                    <v-icon>mdi-delete</v-icon>
                  </v-btn>
                </template>
                <span>{{ $t('oracle_cache_management.delete_tooltip') }}</span>
              </v-tooltip>
            </template>
          </data-table>
        </v-sheet>
      </v-card-text>
    </v-card>
    <confirm-dialog
      :display="confirmClear"
      :title="$tc('oracle_cache_management.delete_confirmation.title')"
      :message="
        $t('oracle_cache_management.delete_confirmation.message', {
          selection,
          fromAsset: deleteFromAsset,
          toAsset: deleteToAsset
        }).toString()
      "
      @confirm="clearCache"
      @cancel="confirmClear = false"
    />
  </fragment>
</template>

<script lang="ts">
import { Severity } from '@rotki/common/lib/messages';
import {
  computed,
  defineComponent,
  onMounted,
  ref,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DataTable from '@/components/helper/DataTable.vue';
import Fragment from '@/components/helper/Fragment';
import OracleEntry from '@/components/settings/OracleEntry.vue';
import i18n from '@/i18n';
import { OracleCacheMeta } from '@/services/balances/types';
import { useAssetInfoRetrieval } from '@/store/assets';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { PriceOracle } from '@/types/user';
import { assert } from '@/utils/assertions';

const headers = computed<DataTableHeader[]>(() => [
  {
    text: i18n.t('oracle_cache_management.headers.from').toString(),
    value: 'fromAsset'
  },
  {
    text: i18n.t('oracle_cache_management.headers.to').toString(),
    value: 'toAsset'
  },
  {
    text: i18n.t('oracle_cache_management.headers.from_date').toString(),
    value: 'fromTimestamp'
  },
  {
    text: i18n.t('oracle_cache_management.headers.to_date').toString(),
    value: 'toTimestamp'
  },
  {
    text: '',
    value: 'actions'
  }
]);

export default defineComponent({
  name: 'OracleCacheManagement',
  components: {
    DataTable,
    ConfirmDialog,
    Fragment,
    OracleEntry
  },
  setup() {
    const { isTaskRunning } = useTasks();
    const { createOracleCache, getPriceCache, deletePriceCache } =
      useBalancePricesStore();

    const oracles: PriceOracle[] = ['cryptocompare'];

    const loading = ref<boolean>(false);
    const confirmClear = ref<boolean>(false);
    const cacheData = ref<OracleCacheMeta[]>([]);
    const fromAsset = ref<string>('');
    const toAsset = ref<string>('');
    const selection = ref<PriceOracle>('cryptocompare');
    const deleteEntry = ref<OracleCacheMeta | null>(null);

    const load = async () => {
      set(loading, true);
      set(cacheData, await getPriceCache('cryptocompare'));
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

    const deleteFromAsset = computed<string>(() => {
      const deleteEntryVal = get(deleteEntry);
      if (deleteEntryVal?.fromAsset) {
        return getAssetSymbol(deleteEntryVal.fromAsset);
      }
      return '';
    });

    const deleteToAsset = computed<string>(() => {
      const deleteEntryVal = get(deleteEntry);
      if (deleteEntryVal?.toAsset) {
        return getAssetSymbol(deleteEntryVal.toAsset);
      }
      return '';
    });

    const pending = isTaskRunning(TaskType.CREATE_PRICE_CACHE);

    const confirmDelete = (entry: OracleCacheMeta) => {
      set(confirmClear, true);
      set(deleteEntry, entry);
    };

    const { notify } = useNotifications();
    const { getAssetSymbol } = useAssetInfoRetrieval();

    const clearCache = async () => {
      const deleteEntryVal = get(deleteEntry);
      assert(deleteEntryVal);
      const { fromAsset, toAsset } = deleteEntryVal;
      set(confirmClear, false);
      set(deleteEntry, null);
      try {
        await deletePriceCache(get(selection), fromAsset, toAsset);
        await load();
      } catch (e: any) {
        const title = i18n
          .t('oracle_cache_management.notification.title')
          .toString();

        const message = i18n
          .t('oracle_cache_management.clear_error', {
            fromAsset: getAssetSymbol(fromAsset),
            toAsset: getAssetSymbol(toAsset),
            error: e.message
          })
          .toString();

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

      const message = status.success
        ? i18n.t('oracle_cache_management.notification.success', {
            fromAsset: getAssetSymbol(fromAssetVal),
            toAsset: getAssetSymbol(toAssetVal),
            source
          })
        : i18n.t('oracle_cache_management.notification.error', {
            fromAsset: getAssetSymbol(fromAssetVal),
            toAsset: getAssetSymbol(toAssetVal),
            source,
            error: status.message
          });
      const title = i18n
        .t('oracle_cache_management.notification.title')
        .toString();

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

    return {
      headers,
      selection,
      oracles,
      fromAsset,
      toAsset,
      filteredData,
      pending,
      loading,
      cacheData,
      confirmClear,
      deleteFromAsset,
      deleteToAsset,
      clearCache,
      confirmDelete,
      fetchPrices,
      clearFilter,
      getAssetSymbol
    };
  }
});
</script>
