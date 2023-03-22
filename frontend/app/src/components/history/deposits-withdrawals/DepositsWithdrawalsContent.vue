<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { Routes } from '@/router/routes';
import {
  type AssetMovement,
  type AssetMovementEntry,
  type AssetMovementRequestPayload
} from '@/types/history/movements';
import { type TradeLocation } from '@/types/history/trade/location';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { SavedFilterLocation } from '@/types/filtering';
import type { Filters, Matcher } from '@/composables/filters/asset-movement';

const props = withDefaults(
  defineProps<{
    locationOverview?: TradeLocation;
    mainPage?: boolean;
  }>(),
  {
    locationOverview: '',
    mainPage: false
  }
);

const { locationOverview, mainPage } = toRefs(props);

const { tc } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => {
  const overview = get(locationOverview);
  const headers: DataTableHeader[] = [
    {
      text: '',
      value: 'ignoredInAccounting',
      sortable: false,
      class: !overview ? 'pa-0' : 'pr-0',
      cellClass: !overview ? 'pa-0' : 'pr-0'
    },
    {
      text: tc('common.location'),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: tc('deposits_withdrawals.headers.action'),
      value: 'category',
      align: 'center',
      class: `text-no-wrap ${overview ? 'pl-0' : ''}`,
      cellClass: overview ? 'pl-0' : ''
    },
    {
      text: tc('common.asset'),
      value: 'asset',
      sortable: false
    },
    {
      text: tc('common.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: tc('deposits_withdrawals.headers.fee'),
      value: 'fee',
      align: 'end'
    },
    {
      text: tc('common.datetime'),
      value: 'timestamp'
    },
    { text: '', value: 'data-table-expand', sortable: false }
  ];

  if (overview) {
    headers.splice(1, 1);
  }

  return headers;
});

const { fetchAssetMovements, refreshAssetMovements } = useAssetMovements();

const {
  options,
  selected,
  expanded,
  isLoading,
  state: assetMovements,
  filters,
  matchers,
  setPage,
  setOptions,
  setFilter,
  applyRouteFilter,
  fetchData
} = useHistoryPaginationFilter<
  AssetMovement,
  AssetMovementRequestPayload,
  AssetMovementEntry,
  Filters,
  Matcher
>(locationOverview, mainPage, useAssetMovementFilters, fetchAssetMovements);

useHistoryAutoRefresh(fetchData);

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.MOVEMENTS,
    toData: (item: AssetMovementEntry) => item.identifier
  },
  selected,
  () => fetchData()
);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.ASSET_MOVEMENT);

const getItemClass = (item: AssetMovementEntry) =>
  item.ignoredInAccounting ? 'darken-row' : '';

const pageRoute = Routes.HISTORY_DEPOSITS_WITHDRAWALS;

onBeforeMount(() => {
  applyRouteFilter();
});

onMounted(async () => {
  await fetchData();
  await refreshAssetMovements();
});

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});
</script>

<template>
  <card outlined-body class="mt-8">
    <template #title>
      <refresh-button
        v-if="!locationOverview"
        :loading="loading"
        :tooltip="tc('deposits_withdrawals.refresh_tooltip')"
        @refresh="refreshAssetMovements(true)"
      />
      <navigator-link :to="{ path: pageRoute }" :enabled="!!locationOverview">
        {{ tc('deposits_withdrawals.title') }}
      </navigator-link>
    </template>
    <template #actions>
      <v-row v-if="!locationOverview">
        <v-col cols="12" sm="6">
          <ignore-buttons
            :disabled="selected.length === 0 || loading"
            @ignore="ignore"
          />
          <div v-if="selected.length > 0" class="mt-2 ms-1">
            {{
              tc('deposits_withdrawals.selected', 0, { count: selected.length })
            }}
            <v-btn small text @click="selected = []">
              {{ tc('common.actions.clear_selection') }}
            </v-btn>
          </div>
        </v-col>
        <v-col cols="12" sm="6">
          <div class="pb-sm-8">
            <table-filter
              :matches="filters"
              :matchers="matchers"
              :location="SavedFilterLocation.HISTORY_DEPOSITS_WITHDRAWALS"
              @update:matches="setFilter($event)"
            />
          </div>
        </v-col>
      </v-row>
    </template>

    <collection-handler :collection="assetMovements" @set-page="setPage">
      <template #default="{ data, limit, total, showUpgradeRow, itemLength }">
        <data-table
          v-model="selected"
          :expanded.sync="expanded"
          :headers="tableHeaders"
          :items="data"
          :loading="isLoading"
          :loading-text="tc('deposits_withdrawals.loading')"
          :options="options"
          :server-items-length="itemLength"
          class="asset-movements"
          :single-select="false"
          :show-select="!locationOverview"
          item-key="identifier"
          show-expand
          single-expand
          multi-sort
          :must-sort="false"
          :item-class="getItemClass"
          @update:options="setOptions($event)"
        >
          <template #item.ignoredInAccounting="{ item, isMobile }">
            <div v-if="item.ignoredInAccounting">
              <badge-display v-if="isMobile" color="grey">
                <v-icon small> mdi-eye-off </v-icon>
                <span class="ml-2">
                  {{ tc('common.ignored_in_accounting') }}
                </span>
              </badge-display>
              <v-tooltip v-else bottom>
                <template #activator="{ on }">
                  <badge-display color="grey" v-on="on">
                    <v-icon small> mdi-eye-off </v-icon>
                  </badge-display>
                </template>
                <span>
                  {{ tc('common.ignored_in_accounting') }}
                </span>
              </v-tooltip>
            </div>
          </template>
          <template #item.location="{ item }">
            <location-display :identifier="item.location" />
          </template>
          <template #item.category="{ item }">
            <badge-display
              :color="
                item.category.toLowerCase() === 'withdrawal' ? 'grey' : 'green'
              "
            >
              {{ item.category }}
            </badge-display>
          </template>
          <template #item.asset="{ item }">
            <asset-details opens-details :asset="item.asset" />
          </template>
          <template #item.amount="{ item }">
            <amount-display
              class="deposits-withdrawals__movement__amount"
              :value="item.amount"
            />
          </template>
          <template #item.fee="{ item }">
            <amount-display
              class="deposits-withdrawals__trade__fee"
              :asset="item.feeAsset"
              :value="item.fee"
            />
          </template>
          <template #item.timestamp="{ item }">
            <date-display :timestamp="item.timestamp" />
          </template>
          <template #expanded-item="{ headers, item }">
            <deposit-withdrawal-details :span="headers.length" :item="item" />
          </template>
          <template v-if="showUpgradeRow" #body.prepend="{ headers }">
            <upgrade-row
              :limit="limit"
              :total="total"
              :colspan="headers.length"
              :label="tc('deposits_withdrawals.label')"
            />
          </template>
        </data-table>
      </template>
    </collection-handler>
  </card>
</template>
