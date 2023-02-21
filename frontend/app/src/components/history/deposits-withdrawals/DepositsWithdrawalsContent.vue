<script setup lang="ts">
import dropRight from 'lodash/dropRight';
import { type Ref } from 'vue';
import { type DataTableHeader } from 'vuetify';
import isEqual from 'lodash/isEqual';
import isEmpty from 'lodash/isEmpty';
import { Routes } from '@/router/routes';
import {
  type AssetMovement,
  type AssetMovementEntry,
  type AssetMovementRequestPayload
} from '@/types/history/movements';
import { type TradeLocation } from '@/types/history/trade/location';
import { Section } from '@/types/status';
import { type TradeEntry } from '@/types/history/trade';
import { IgnoreActionType } from '@/types/history/ignored';
import { type TablePagination } from '@/types/pagination';
import {
  type LocationQuery,
  RouterPaginationOptionsSchema
} from '@/types/route';

const props = withDefaults(
  defineProps<{
    locationOverview?: TradeLocation;
    readFilterFromRoute?: boolean;
  }>(),
  {
    locationOverview: '',
    readFilterFromRoute: false
  }
);

const emit = defineEmits<{
  (e: 'fetch', refresh: boolean): void;
  (e: 'update:query-params', params: LocationQuery): void;
}>();

const { locationOverview, readFilterFromRoute } = toRefs(props);

const selected: Ref<AssetMovementEntry[]> = ref([]);
const expanded: Ref<TradeEntry[]> = ref([]);
const options: Ref<TablePagination<AssetMovement> | null> = ref(null);

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

const assetMovementStore = useAssetMovements();
const { assetMovements } = storeToRefs(assetMovementStore);
const { updateAssetMovementsPayload } = assetMovementStore;

const route = useRoute();

const { filters, matchers, updateFilter, RouteFilterSchema } =
  useAssetMovementFilters();

// If using route filter is true, then we shouldn't move the page back to 1, but use the page param from route query instead
const applyingRouteFilter: Ref<boolean> = ref(false);

const applyRouteFilter = () => {
  if (!get(readFilterFromRoute)) return;

  const query = get(route).query;
  const parsedOptions = RouterPaginationOptionsSchema.parse(query);
  const parsedFilters = RouteFilterSchema.parse(query);
  set(applyingRouteFilter, true);
  updateFilter(parsedFilters);
  set(options, parsedOptions);
};

watch(
  () => get(route).query?.page,
  (page, oldPage) => {
    if (page !== oldPage) {
      applyRouteFilter();
    }
  }
);

onBeforeMount(() => {
  applyRouteFilter();
});

const updatePayloadHandler = async (firstLoad = false) => {
  let paginationOptions = {};
  let routerQuery = {};

  const optionsVal = get(options);
  if (optionsVal) {
    const { itemsPerPage, page, sortBy, sortDesc } = optionsVal;
    const offset = (page - 1) * itemsPerPage;

    routerQuery = {
      itemsPerPage,
      page,
      sortBy,
      sortDesc
    };

    paginationOptions = {
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy.length > 0 ? sortBy : ['timestamp'],
      ascending:
        sortDesc.length > 1 ? dropRight(sortDesc).map(bool => !bool) : [false]
    };
  }

  routerQuery = {
    ...routerQuery,
    ...get(filters)
  };

  if (get(locationOverview)) {
    filters.value.location = get(locationOverview) as TradeLocation;
  }

  const payload: Partial<AssetMovementRequestPayload> = {
    ...(get(filters) as Partial<AssetMovementRequestPayload>),
    ...paginationOptions
  };

  await updateAssetMovementsPayload(payload);

  if (!firstLoad) {
    emit('update:query-params', routerQuery);
  }
};

const updatePaginationHandler = async (
  newOptions: TablePagination<AssetMovement> | null
) => {
  const firstLoad = !get(options) || isEmpty(get(options));
  set(options, newOptions);
  await updatePayloadHandler(firstLoad);
};

watch(filters, async (filters, oldFilters) => {
  if (isEqual(filters, oldFilters)) {
    set(applyingRouteFilter, false);
    return;
  }

  if (!get(applyingRouteFilter)) {
    setPage(1);
  } else {
    set(applyingRouteFilter, false);
    await updatePayloadHandler();
  }
});

const setPage = (page: number) => {
  const optionsVal = get(options);
  if (optionsVal) {
    updatePaginationHandler({ ...optionsVal, page });
  }
};

const fetch = (refresh = false) => emit('fetch', refresh);

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.MOVEMENTS,
    toData: (item: AssetMovementEntry) => item.identifier
  },
  selected,
  fetch
);

const loading = isSectionLoading(Section.ASSET_MOVEMENT);

const getItemClass = (item: AssetMovementEntry) => {
  return item.ignoredInAccounting ? 'darken-row' : '';
};

const pageRoute = Routes.HISTORY_DEPOSITS_WITHDRAWALS;
</script>

<template>
  <card outlined-body>
    <template #title>
      <refresh-button
        v-if="!locationOverview"
        :loading="loading"
        :tooltip="tc('deposits_withdrawals.refresh_tooltip')"
        @refresh="fetch(true)"
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
              @update:matches="updateFilter($event)"
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
          :loading="loading"
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
          @update:options="updatePaginationHandler($event)"
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
