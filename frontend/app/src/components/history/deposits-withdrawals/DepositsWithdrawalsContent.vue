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
              :matchers="matchers"
              @update:matches="updateFilter($event)"
            />
          </div>
        </v-col>
      </v-row>
    </template>
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
      :item-class="getClass"
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
  </card>
</template>

<script setup lang="ts">
import { dropRight } from 'lodash';
import { PropType, Ref } from 'vue';
import { DataTableHeader } from 'vuetify';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import DataTable from '@/components/helper/DataTable.vue';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import DepositWithdrawalDetails from '@/components/history/deposits-withdrawals/DepositWithdrawalDetails.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { isSectionLoading } from '@/composables/common';
import { useAssetMovementFilters } from '@/composables/filters/asset-movement';
import { setupIgnore } from '@/composables/history';
import { Routes } from '@/router/routes';
import { useAssetMovements } from '@/store/history/asset-movements';
import {
  AssetMovementEntry,
  IgnoreActionType,
  TradeEntry
} from '@/store/history/types';
import { Collection } from '@/types/collection';
import {
  AssetMovement,
  AssetMovementRequestPayload
} from '@/types/history/movements';
import { TradeLocation } from '@/types/history/trade-location';
import { Section } from '@/types/status';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof AssetMovement)[];
  sortDesc: boolean[];
};

const props = defineProps({
  locationOverview: {
    required: false,
    type: String as PropType<TradeLocation | ''>,
    default: ''
  }
});

const emit = defineEmits<{
  (e: 'fetch', refresh: boolean): void;
}>();

const { locationOverview } = toRefs(props);

const selected: Ref<AssetMovementEntry[]> = ref([]);
const expanded: Ref<TradeEntry[]> = ref([]);
const options: Ref<PaginationOptions | null> = ref(null);

const { tc } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => {
  let overview = get(locationOverview);
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

const { data, limit, found, total } = getCollectionData<AssetMovementEntry>(
  assetMovements as Ref<Collection<AssetMovementEntry>>
);

const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

const fetch = (refresh: boolean = false) => emit('fetch', refresh);

const { ignore } = setupIgnore(
  IgnoreActionType.MOVEMENTS,
  selected,
  fetch,
  (item: AssetMovementEntry) => item.identifier
);
const { filters, matchers, updateFilter } = useAssetMovementFilters();
const loading = isSectionLoading(Section.ASSET_MOVEMENT);

const updatePayloadHandler = async () => {
  let paginationOptions = {};
  const optionsVal = get(options);
  if (optionsVal) {
    const { itemsPerPage, page, sortBy, sortDesc } = get(options)!;
    const offset = (page - 1) * itemsPerPage;

    paginationOptions = {
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy.length > 0 ? sortBy : ['timestamp'],
      ascending:
        sortDesc.length > 1 ? dropRight(sortDesc).map(bool => !bool) : [false]
    };
  }

  if (get(locationOverview)) {
    filters.value.location = get(locationOverview) as TradeLocation;
  }

  const payload: Partial<AssetMovementRequestPayload> = {
    ...(get(filters) as Partial<AssetMovementRequestPayload>),
    ...paginationOptions
  };

  await updateAssetMovementsPayload(payload);
};

const updatePaginationHandler = async (
  newOptions: PaginationOptions | null
) => {
  set(options, newOptions);
  await updatePayloadHandler();
};

const getClass = (item: AssetMovementEntry) => {
  return item.ignoredInAccounting ? 'darken-row' : '';
};

watch(filters, async (filter, oldValue) => {
  if (filter === oldValue) {
    return;
  }
  let newOptions = null;
  if (get(options)) {
    newOptions = {
      ...get(options)!,
      page: 1
    };
  }

  await updatePaginationHandler(newOptions);
});

const pageRoute = Routes.HISTORY_DEPOSITS_WITHDRAWALS;
</script>
