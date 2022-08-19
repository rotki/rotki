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
      multi-sort
      :must-sort="false"
      :item-class="item => (item.ignoredInAccounting ? 'darken-row' : '')"
      @update:options="updatePaginationHandler($event)"
    >
      <template #item.ignoredInAccounting="{ item, isMobile }">
        <div v-if="item.ignoredInAccounting">
          <badge-display v-if="isMobile" color="grey">
            <v-icon small> mdi-eye-off </v-icon>
            <span class="ml-2">
              {{ $t('common.ignored_in_accounting') }}
            </span>
          </badge-display>
          <v-tooltip v-else bottom>
            <template #activator="{ on }">
              <badge-display color="grey" v-on="on">
                <v-icon small> mdi-eye-off </v-icon>
              </badge-display>
            </template>
            <span>
              {{ $t('common.ignored_in_accounting') }}
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
import { dropRight } from 'lodash';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
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
import { setupIgnore } from '@/composables/history';
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
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { Collection } from '@/types/collection';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';
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
    const { supportedAssetsSymbol } = toRefs(assetInfoRetrievalStore);
    const { getAssetIdentifierForSymbol } = assetInfoRetrievalStore;

    const { associatedLocations } = storeToRefs(historyStore);
    const { assetMovements } = storeToRefs(assetMovementStore);

    const { updateAssetMovementsPayload } = assetMovementStore;

    const { data, limit, found, total } = getCollectionData<AssetMovementEntry>(
      assetMovements as Ref<Collection<AssetMovementEntry>>
    );

    const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

    const expanded: Ref<TradeEntry[]> = ref([]);

    const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());

    const options: Ref<PaginationOptions | null> = ref(null);
    const filters: Ref<MatchedKeyword<AssetMovementFilterValueKeys>> = ref({});

    const { tc } = useI18n();

    const tableHeaders = computed<DataTableHeader[]>(() => {
      const headers: DataTableHeader[] = [
        {
          text: '',
          value: 'ignoredInAccounting',
          sortable: false,
          class: !locationOverview ? 'pa-0' : 'pr-0',
          cellClass: !locationOverview ? 'pa-0' : 'pr-0'
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
          class: `text-no-wrap ${locationOverview ? 'pl-0' : ''}`,
          cellClass: locationOverview ? 'pl-0' : ''
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

      if (get(locationOverview)) {
        headers.splice(1, 1);
      }

      return headers;
    });

    const matchers = computed<
      SearchMatcher<AssetMovementFilterKeys, AssetMovementFilterValueKeys>[]
    >(() => [
      {
        key: AssetMovementFilterKeys.ASSET,
        keyValue: AssetMovementFilterValueKeys.ASSET,
        description: tc('deposit_withdrawals.filter.asset'),
        suggestions: () => get(supportedAssetsSymbol),
        validate: (asset: string) => get(supportedAssetsSymbol).includes(asset),
        transformer: (asset: string) => getAssetIdentifierForSymbol(asset) ?? ''
      },
      {
        key: AssetMovementFilterKeys.ACTION,
        keyValue: AssetMovementFilterValueKeys.ACTION,
        description: tc('deposit_withdrawals.filter.action'),
        suggestions: () => MovementCategory.options,
        validate: type => (MovementCategory.options as string[]).includes(type)
      },
      {
        key: AssetMovementFilterKeys.START,
        keyValue: AssetMovementFilterValueKeys.START,
        description: tc('deposit_withdrawals.filter.start_date'),
        suggestions: () => [],
        hint: tc('deposit_withdrawals.filter.date_hint', 0, {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
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
        description: tc('deposit_withdrawals.filter.end_date'),
        suggestions: () => [],
        hint: tc('deposit_withdrawals.filter.date_hint', 0, {
          format: getDateInputISOFormat(get(dateInputFormat))
        }),
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
        description: tc('deposit_withdrawals.filter.location'),
        suggestions: () => get(associatedLocations),
        validate: location => get(associatedLocations).includes(location as any)
      }
    ]);

    const updatePayloadHandler = () => {
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
            sortDesc.length > 1
              ? dropRight(sortDesc).map(bool => !bool)
              : [false]
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
      tableHeaders,
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
      ...setupIgnore(IgnoreActionType.MOVEMENTS, selected, data, fetch, getId),
      tc
    };
  }
});
</script>
