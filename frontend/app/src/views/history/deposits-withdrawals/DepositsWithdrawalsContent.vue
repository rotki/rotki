<template>
  <card outlined-body>
    <template #title>
      <refresh-button
        v-if="!locationOverview"
        :loading="loading"
        :tooltip="$t('deposits_withdrawals.refresh_tooltip')"
        @refresh="fetch(true)"
      />
      <navigator-link :to="{ path: pageRoute }" :enabled="!!locationOverview">
        {{ $t('deposits_withdrawals.title') }}
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
              $t('deposits_withdrawals.selected', { count: selected.length })
            }}
            <v-btn small text @click="selected = []">
              {{ $t('deposits_withdrawals.clear_selection') }}
            </v-btn>
          </div>
        </v-col>
        <v-col cols="12" sm="6">
          <div class="pb-sm-8">
            <table-filter
              :matchers="matchers"
              @update:matches="updateFilterHandler($event)"
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
      :item-class="item => (item.ignoredInAccounting ? 'darken-row' : '')"
      @update:options="updatePaginationHandler($event)"
    >
      <template #item.ignoredInAccounting="{ item, isMobile }">
        <div v-if="item.ignoredInAccounting">
          <badge-display v-if="isMobile" color="grey">
            <v-icon small> mdi-eye-off </v-icon>
            <span class="ml-2">
              {{ $t('deposits_withdrawals.headers.ignored') }}
            </span>
          </badge-display>
          <v-tooltip v-else bottom>
            <template #activator="{ on }">
              <badge-display color="grey" v-on="on">
                <v-icon small> mdi-eye-off </v-icon>
              </badge-display>
            </template>
            <span>
              {{ $t('deposits_withdrawals.headers.ignored') }}
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
      <template #item.time="{ item }">
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
          :label="$t('deposits_withdrawals.label')"
        />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import DataTable from '@/components/helper/DataTable.vue';
import NavigatorLink from '@/components/helper/NavigatorLink.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { isSectionLoading } from '@/composables/common';
import {
  getCollectionData,
  setupEntryLimit,
  setupIgnore
} from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import {
  AssetMovement,
  AssetMovementRequestPayload,
  MovementCategory,
  TradeLocation
} from '@/services/history/types';
import { useAssetInfoRetrieval } from '@/store/assets';
import { Section } from '@/store/const';
import { useAssetMovements, useHistory } from '@/store/history';
import {
  AssetMovementEntry,
  IgnoreActionType,
  TradeEntry
} from '@/store/history/types';
import { Collection } from '@/types/collection';
import { uniqueStrings } from '@/utils/data';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import DepositWithdrawalDetails from '@/views/history/deposits-withdrawals/DepositWithdrawalDetails.vue';

enum AssetMovementFilterKeys {
  LOCATION = 'location',
  ACTION = 'action',
  ASSET = 'asset',
  START = 'start',
  END = 'end'
}

enum AssetMovementFilterValueKeys {
  LOCATION = 'location',
  ACTION = 'action',
  ASSET = 'asset',
  START = 'fromTimestamp',
  END = 'toTimestamp'
}

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof AssetMovement)[];
  sortDesc: boolean[];
};

const tableHeaders = (locationOverview: string): DataTableHeader[] => {
  const headers: DataTableHeader[] = [
    {
      text: '',
      value: 'ignoredInAccounting',
      sortable: false,
      class: !locationOverview ? 'pa-0' : 'pr-0',
      cellClass: !locationOverview ? 'pa-0' : 'pr-0'
    },
    {
      text: i18n.t('deposits_withdrawals.headers.location').toString(),
      value: 'location',
      width: '120px',
      align: 'center'
    },
    {
      text: i18n.t('deposits_withdrawals.headers.action').toString(),
      value: 'category',
      align: 'center',
      class: `text-no-wrap ${locationOverview ? 'pl-0' : ''}`,
      cellClass: locationOverview ? 'pl-0' : ''
    },
    {
      text: i18n.t('deposits_withdrawals.headers.asset').toString(),
      value: 'asset',
      sortable: false
    },
    {
      text: i18n.t('deposits_withdrawals.headers.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: i18n.t('deposits_withdrawals.headers.fee').toString(),
      value: 'fee',
      align: 'end'
    },
    {
      text: i18n.t('deposits_withdrawals.headers.timestamp').toString(),
      value: 'time'
    },
    { text: '', value: 'data-table-expand', sortable: false }
  ];

  if (locationOverview) {
    headers.splice(1, 1);
  }

  return headers;
};

export default defineComponent({
  name: 'DepositsWithdrawalsContent',
  components: {
    NavigatorLink,
    BadgeDisplay,
    TableFilter,
    DepositWithdrawalDetails,
    DataTable,
    IgnoreButtons,
    RefreshButton,
    UpgradeRow,
    AssetDetails,
    LocationDisplay,
    DateDisplay
  },
  props: {
    locationOverview: {
      required: false,
      type: String as PropType<TradeLocation | ''>,
      default: ''
    }
  },
  emits: ['fetch'],
  setup(props, { emit }) {
    const { locationOverview } = toRefs(props);

    const fetch = (refresh: boolean = false) => emit('fetch', refresh);

    const historyStore = useHistory();
    const assetMovementStore = useAssetMovements();
    const assetInfoRetrievalStore = useAssetInfoRetrieval();
    const { supportedAssets } = toRefs(assetInfoRetrievalStore);
    const { getAssetSymbol, getAssetIdentifierForSymbol } =
      assetInfoRetrievalStore;

    const { associatedLocations } = storeToRefs(historyStore);
    const { assetMovements } = storeToRefs(assetMovementStore);

    const { updateAssetMovementsPayload } = assetMovementStore;

    const { data, limit, found, total } = getCollectionData<AssetMovementEntry>(
      assetMovements as Ref<Collection<AssetMovementEntry>>
    );

    const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

    const expanded: Ref<TradeEntry[]> = ref([]);

    const { dateInputFormat } = setupSettings();

    const options: Ref<PaginationOptions | null> = ref(null);
    const filters: Ref<MatchedKeyword<AssetMovementFilterValueKeys>> = ref({});

    const availableAssets = computed<string[]>(() => {
      return get(supportedAssets)
        .map(value => getAssetSymbol(value.identifier))
        .filter(uniqueStrings);
    });

    const availableLocations = computed<TradeLocation[]>(() => {
      return get(associatedLocations);
    });

    const matchers = computed<
      SearchMatcher<AssetMovementFilterKeys, AssetMovementFilterValueKeys>[]
    >(() => [
      {
        key: AssetMovementFilterKeys.ASSET,
        keyValue: AssetMovementFilterValueKeys.ASSET,
        description: i18n.t('deposit_withdrawals.filter.asset').toString(),
        suggestions: () => get(availableAssets),
        validate: (asset: string) => get(availableAssets).includes(asset),
        transformer: (asset: string) => getAssetIdentifierForSymbol(asset) ?? ''
      },
      {
        key: AssetMovementFilterKeys.ACTION,
        keyValue: AssetMovementFilterValueKeys.ACTION,
        description: i18n.t('deposit_withdrawals.filter.action').toString(),
        suggestions: () => MovementCategory.options,
        validate: type => (MovementCategory.options as string[]).includes(type)
      },
      {
        key: AssetMovementFilterKeys.START,
        keyValue: AssetMovementFilterValueKeys.START,
        description: i18n.t('deposit_withdrawals.filter.start_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('deposit_withdrawals.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, get(dateInputFormat)))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      },
      {
        key: AssetMovementFilterKeys.END,
        keyValue: AssetMovementFilterValueKeys.END,
        description: i18n.t('deposit_withdrawals.filter.end_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('deposit_withdrawals.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, get(dateInputFormat)))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      },
      {
        key: AssetMovementFilterKeys.LOCATION,
        keyValue: AssetMovementFilterValueKeys.LOCATION,
        description: i18n.t('deposit_withdrawals.filter.location').toString(),
        suggestions: () => get(availableLocations),
        validate: location => get(availableLocations).includes(location as any)
      }
    ]);

    const updatePayloadHandler = () => {
      let paginationOptions = {};
      const optionsVal = get(options);
      if (optionsVal) {
        set(options, {
          ...optionsVal,
          sortBy: optionsVal.sortBy.length > 0 ? [optionsVal.sortBy[0]] : [],
          sortDesc:
            optionsVal.sortDesc.length > 0 ? [optionsVal.sortDesc[0]] : []
        });

        const { itemsPerPage, page, sortBy, sortDesc } = get(options)!;
        const offset = (page - 1) * itemsPerPage;

        paginationOptions = {
          limit: itemsPerPage,
          offset,
          orderByAttribute: sortBy.length > 0 ? sortBy[0] : 'time',
          ascending: !sortDesc[0]
        };
      }

      if (get(locationOverview)) {
        filters.value.location = get(locationOverview) as TradeLocation;
      }

      const payload: Partial<AssetMovementRequestPayload> = {
        ...(get(filters) as Partial<AssetMovementRequestPayload>),
        ...paginationOptions
      };

      updateAssetMovementsPayload(payload);
    };

    const updatePaginationHandler = (newOptions: PaginationOptions | null) => {
      set(options, newOptions);
      updatePayloadHandler();
    };

    const updateFilterHandler = (
      newFilters: MatchedKeyword<AssetMovementFilterKeys>
    ) => {
      set(filters, newFilters);

      let newOptions = null;
      if (get(options)) {
        newOptions = {
          ...get(options)!,
          page: 1
        };
      }

      updatePaginationHandler(newOptions);
    };

    const getId = (item: AssetMovementEntry) => item.identifier;
    const selected: Ref<AssetMovementEntry[]> = ref([]);

    const pageRoute = Routes.HISTORY_DEPOSITS_WITHDRAWALS.route;

    return {
      pageRoute,
      selected,
      tableHeaders: tableHeaders(get(locationOverview)),
      data,
      limit,
      found,
      total,
      itemLength,
      fetch,
      showUpgradeRow,
      loading: isSectionLoading(Section.ASSET_MOVEMENT),
      expanded,
      options,
      matchers,
      updatePaginationHandler,
      updateFilterHandler,
      ...setupIgnore(IgnoreActionType.MOVEMENTS, selected, data, fetch, getId)
    };
  }
});
</script>
