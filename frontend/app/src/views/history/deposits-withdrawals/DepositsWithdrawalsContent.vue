<template>
  <card outlined-body>
    <template #title>
      <refresh-button
        :loading="refreshing"
        :tooltip="$t('deposits_withdrawals.refresh_tooltip')"
        @refresh="fetch(true)"
      />
      {{ $t('deposits_withdrawals.title') }}
    </template>
    <template #actions>
      <v-row>
        <v-col cols="12" sm="6">
          <ignore-buttons
            :disabled="selected.length === 0 || loading || refreshing"
            @ignore="ignore"
          />
          <div v-if="selected.length > 0" class="mt-2 ms-1">
            {{
              $t('deposits_withdrawals.selected', { count: selected.length })
            }}
            <v-btn small text @click="setAllSelected(false)">
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
      :expanded.sync="expanded"
      :headers="tableHeaders"
      :items="assetMovements"
      :loading="refreshing"
      :options="options"
      :server-items-length="itemLength"
      class="asset-movements"
      item-key="identifier"
      show-expand
      single-expand
      @update:options="updatePaginationHandler($event)"
    >
      <template #header.selection>
        <v-simple-checkbox
          :ripple="false"
          :value="isAllSelected"
          color="primary"
          @input="setAllSelected($event)"
        />
      </template>
      <template #item.selection="{ item }">
        <v-simple-checkbox
          :ripple="false"
          color="primary"
          :value="isSelected(item.identifier)"
          @input="selectionChanged(item.identifier, $event)"
        />
      </template>
      <template #item.ignoredInAccounting="{ item }">
        <v-icon v-if="item.ignoredInAccounting">mdi-check</v-icon>
      </template>
      <template #item.location="{ item }">
        <location-display :identifier="item.location" />
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
import { computed, defineComponent, Ref, ref } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import DateDisplay from '@/components/display/DateDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import {
  setupAssetInfoRetrieval,
  setupSupportedAssets
} from '@/composables/balances';
import { setupStatusChecking } from '@/composables/common';
import {
  setupAssetMovements,
  setupAssociatedLocations,
  setupEntryLimit
} from '@/composables/history';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import {
  AssetMovement,
  AssetMovementRequestPayload,
  MovementCategory,
  TradeLocation
} from '@/services/history/types';
import { Section } from '@/store/const';
import {
  AssetMovementEntry,
  IgnoreActionType,
  TradeEntry
} from '@/store/history/types';
import { uniqueStrings } from '@/utils/data';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import { setupIgnore } from '@/views/history/composables/ignore';
import { setupSelectionMode } from '@/views/history/composables/selection';
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

const tableHeaders: DataTableHeader[] = [
  { text: '', value: 'selection', width: '34px', sortable: false },
  {
    text: i18n.t('deposits_withdrawals.headers.location').toString(),
    value: 'location',
    width: '120px',
    align: 'center'
  },
  {
    text: i18n.t('deposits_withdrawals.headers.action').toString(),
    value: 'category'
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
  {
    text: i18n.t('deposits_withdrawals.headers.ignored').toString(),
    value: 'ignoredInAccounting',
    sortable: false
  },
  { text: '', value: 'data-table-expand', sortable: false }
];

export default defineComponent({
  name: 'DepositsWithdrawalsContent',
  components: {
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
  setup(_, { emit }) {
    const fetch = (refresh: boolean = false) => emit('fetch', refresh);
    const updatePayload = (payload: Partial<AssetMovementRequestPayload>) =>
      emit('update:payload', payload);

    const { assetMovements, limit, found, total } = setupAssetMovements();

    const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const expanded: Ref<TradeEntry[]> = ref([]);

    const { getAssetSymbol, getAssetIdentifierForSymbol } =
      setupAssetInfoRetrieval();

    const { dateInputFormat } = setupSettings();

    const options: Ref<PaginationOptions | null> = ref(null);
    const filters: Ref<MatchedKeyword<AssetMovementFilterValueKeys>> = ref({});

    const { supportedAssets } = setupSupportedAssets();
    const availableAssets = computed<string[]>(() => {
      return supportedAssets.value
        .map(value => getAssetSymbol(value.identifier))
        .filter(uniqueStrings);
    });

    const { associatedLocations } = setupAssociatedLocations();
    const availableLocations = computed<TradeLocation[]>(() => {
      return associatedLocations.value;
    });

    const matchers = computed<
      SearchMatcher<AssetMovementFilterKeys, AssetMovementFilterValueKeys>[]
    >(() => [
      {
        key: AssetMovementFilterKeys.ASSET,
        keyValue: AssetMovementFilterValueKeys.ASSET,
        description: i18n.t('deposit_withdrawals.filter.asset').toString(),
        suggestions: () => availableAssets.value,
        validate: (asset: string) => availableAssets.value.includes(asset),
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
            format: getDateInputISOFormat(dateInputFormat.value)
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, dateInputFormat.value))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, dateInputFormat.value).toString()
      },
      {
        key: AssetMovementFilterKeys.END,
        keyValue: AssetMovementFilterValueKeys.END,
        description: i18n.t('deposit_withdrawals.filter.end_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('deposit_withdrawals.filter.date_hint', {
            format: getDateInputISOFormat(dateInputFormat.value)
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, dateInputFormat.value))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, dateInputFormat.value).toString()
      },
      {
        key: AssetMovementFilterKeys.LOCATION,
        keyValue: AssetMovementFilterValueKeys.LOCATION,
        description: i18n.t('deposit_withdrawals.filter.location').toString(),
        suggestions: () => availableLocations.value,
        validate: location => availableLocations.value.includes(location as any)
      }
    ]);

    const updatePayloadHandler = () => {
      let paginationOptions = {};
      if (options.value) {
        options.value = {
          ...options.value,
          sortBy:
            options.value.sortBy.length > 0 ? [options.value.sortBy[0]] : [],
          sortDesc:
            options.value.sortDesc.length > 0 ? [options.value.sortDesc[0]] : []
        };

        const { itemsPerPage, page, sortBy, sortDesc } = options.value;
        const offset = (page - 1) * itemsPerPage;

        paginationOptions = {
          limit: itemsPerPage,
          offset,
          orderByAttribute: sortBy.length > 0 ? sortBy[0] : 'time',
          ascending: !sortDesc[0]
        };
      }

      const payload: Partial<AssetMovementRequestPayload> = {
        ...filters.value,
        ...paginationOptions
      };

      updatePayload(payload);
    };

    const updatePaginationHandler = (newOptions: PaginationOptions | null) => {
      options.value = newOptions;
      updatePayloadHandler();
    };

    const updateFilterHandler = (
      newFilters: MatchedKeyword<AssetMovementFilterKeys>
    ) => {
      filters.value = newFilters;

      let newOptions = null;
      if (options.value) {
        newOptions = {
          ...options.value,
          page: 1
        };
      }

      updatePaginationHandler(newOptions);
    };

    const getId = (item: AssetMovementEntry) => item.identifier;

    const selectionMode = setupSelectionMode<AssetMovementEntry>(
      assetMovements,
      getId
    );

    return {
      tableHeaders,
      assetMovements,
      limit,
      found,
      total,
      itemLength,
      fetch,
      showUpgradeRow,
      updatePayload,
      loading: shouldShowLoadingScreen(Section.ASSET_MOVEMENT),
      refreshing: isSectionRefreshing(Section.ASSET_MOVEMENT),
      expanded,
      options,
      matchers,
      updatePaginationHandler,
      updateFilterHandler,
      ...selectionMode,
      ...setupIgnore(
        IgnoreActionType.MOVEMENTS,
        selectionMode.selected,
        assetMovements,
        fetch,
        getId
      )
    };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
  th {
    &:nth-child(2) {
      span {
        padding-left: 16px;
      }
    }
  }
}
</style>
