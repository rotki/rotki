<script setup lang="ts">
import dropRight from 'lodash/dropRight';
import { type ComputedRef, type Ref, type UnwrapRef } from 'vue';
import { type DataTableHeader } from 'vuetify';
import isEqual from 'lodash/isEqual';
import { type MaybeRef } from '@vueuse/core';
import { Routes } from '@/router/routes';
import {
  type AssetMovement,
  type AssetMovementEntry,
  type AssetMovementRequestPayload
} from '@/types/history/movements';
import { type TradeLocation } from '@/types/history/trade/location';
import { Section } from '@/types/status';
import { IgnoreActionType } from '@/types/history/ignored';
import { type TablePagination } from '@/types/pagination';
import {
  type LocationQuery,
  RouterPaginationOptionsSchema
} from '@/types/route';
import { type Collection } from '@/types/collection';
import { defaultCollectionState, defaultOptions } from '@/utils/collection';
import { assert } from '@/utils/assertions';
import { SavedFilterLocation } from '@/types/filtering';

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

const selected: Ref<AssetMovementEntry[]> = ref([]);
const expanded: Ref<AssetMovementEntry[]> = ref([]);
const options: Ref<TablePagination<AssetMovement>> = ref(defaultOptions());
const userAction: Ref<boolean> = ref(false);

const { tc } = useI18n();

const pageParams: ComputedRef<AssetMovementRequestPayload> = computed(() => {
  const { itemsPerPage, page, sortBy, sortDesc } = get(options);
  const offset = (page - 1) * itemsPerPage;

  const selectedFilters = get(filters);
  const overview = get(locationOverview);
  if (overview) {
    selectedFilters.location = overview;
  }

  return {
    ...(selectedFilters as Partial<AssetMovementRequestPayload>),
    limit: itemsPerPage,
    offset,
    orderByAttributes: sortBy?.length > 0 ? sortBy : ['timestamp'],
    ascending:
      sortDesc && sortDesc.length > 1
        ? dropRight(sortDesc).map(bool => !bool)
        : [false]
  };
});

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
  isLoading,
  state: assetMovements,
  execute
} = useAsyncState<
  Collection<AssetMovementEntry>,
  MaybeRef<AssetMovementRequestPayload>[]
>(args => fetchAssetMovements(args), defaultCollectionState(), {
  immediate: false,
  resetOnExecute: false,
  delay: 0
});

const router = useRouter();
const route = useRoute();

const { filters, matchers, updateFilter, RouteFilterSchema } =
  useAssetMovementFilters();

const applyRouteFilter = () => {
  if (!get(mainPage)) {
    return;
  }

  const query = get(route).query;
  const parsedOptions = RouterPaginationOptionsSchema.parse(query);
  const parsedFilters = RouteFilterSchema.parse(query);

  updateFilter(parsedFilters);
  set(options, {
    ...get(options),
    ...parsedOptions
  });
};

watch(route, () => {
  set(userAction, false);
  applyRouteFilter();
});

onBeforeMount(() => {
  applyRouteFilter();
});

watch(filters, async (filters, oldFilters) => {
  if (isEqual(filters, oldFilters)) {
    return;
  }

  set(options, { ...get(options), page: 1 });
});

const setPage = (page: number) => {
  set(userAction, true);
  set(options, { ...get(options), page });
};

const setOptions = (newOptions: TablePagination<AssetMovement>) => {
  set(userAction, true);
  set(options, newOptions);
};

const setFilter = (newFilter: UnwrapRef<typeof filters>) => {
  set(userAction, true);
  updateFilter(newFilter);
};

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.MOVEMENTS,
    toData: (item: AssetMovementEntry) => item.identifier
  },
  selected,
  () => fetchData()
);

onMounted(async () => {
  await fetchData();
  await refreshAssetMovements();
});

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.ASSET_MOVEMENT);

const getItemClass = (item: AssetMovementEntry) =>
  item.ignoredInAccounting ? 'darken-row' : '';

const pageRoute = Routes.HISTORY_DEPOSITS_WITHDRAWALS;

const getQuery = (): LocationQuery => {
  const opts = get(options);
  assert(opts);
  const { itemsPerPage, page, sortBy, sortDesc } = opts;

  const selectedFilters = get(filters);

  const overview = get(locationOverview);
  if (overview) {
    selectedFilters.location = overview;
  }

  return {
    itemsPerPage: itemsPerPage.toString(),
    page: page.toString(),
    sortBy,
    sortDesc: sortDesc.map(x => x.toString()),
    ...selectedFilters
  };
};

const fetchData = async (): Promise<void> => {
  await execute(0, pageParams);
};

useHistoryAutoRefresh(() => fetchData());

watch(pageParams, async (params, op) => {
  if (isEqual(params, op)) {
    return;
  }
  if (get(userAction) && get(mainPage)) {
    // Route should only be updated on user action otherwise it messes with
    // forward navigation.
    await router.push({
      query: getQuery()
    });
    set(userAction, false);
  }

  await fetchData();
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
