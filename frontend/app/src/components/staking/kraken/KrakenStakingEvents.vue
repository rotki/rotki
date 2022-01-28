<template>
  <card outlined-body>
    <template #title>
      <refresh-button
        :loading="loading"
        :tooltip="$t('kraken_staking_events.refresh_tooltip')"
        @refresh="refresh"
      />
      {{ $t('kraken_staking_events.titles') }}
      <v-icon v-if="loading" color="primary" class="ml-2">
        mdi-spin mdi-loading
      </v-icon>
    </template>
    <template #actions>
      <v-row>
        <v-col cols="12" offset-md="6" md="6">
          <table-filter :matchers="matchers" @update:matches="updateFilter" />
        </v-col>
      </v-row>
    </template>
    <data-table
      :items="events.events"
      :headers="tableHeaders"
      :options.sync="options"
      :server-items-length="events.entriesFound"
      sort-by="timestamp"
    >
      <template v-if="showUpgradeRow" #body.prepend="{ headers }">
        <upgrade-row
          :limit="events.entriesLimit"
          :total="events.entriesTotal"
          :colspan="headers.length"
          :label="$t('kraken_staking_events.upgrade.label')"
        />
      </template>
      <template #item.eventType="{ item }">
        {{ item.eventType }}
      </template>
      <template #item.asset="{ item }">
        <asset-details :asset="item.asset" />
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display :value="item.usdValue" />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
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
  toRefs,
  unref,
  watch
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { setupAssetInfoRetrieval } from '@/composables/balances';
import { setupThemeCheck } from '@/composables/common';
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import {
  KrakenStakingEvents,
  KrakenStakingEventType,
  KrakenStakingPagination,
  KrakenStakingPaginationOptions
} from '@/types/staking';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

const getHeaders = (): DataTableHeader[] => [
  {
    text: i18n.t('kraken_staking_events.column.event_type').toString(),
    value: 'eventType'
  },
  {
    text: i18n.t('kraken_staking_events.column.asset').toString(),
    value: 'asset'
  },
  {
    text: i18n.t('kraken_staking_events.column.time').toString(),
    value: 'timestamp'
  },
  {
    text: i18n.t('kraken_staking_events.column.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: i18n.t('kraken_staking_events.column.value').toString(),
    value: 'usdValue',
    align: 'end'
  }
];

enum KrakenStakingKeys {
  TYPE = 'type',
  ASSET = 'asset',
  START = 'start',
  END = 'end'
}

enum KrakenStakingValueKeys {
  TYPE = 'eventSubtypes',
  ASSET = 'asset',
  START = 'fromTimestamp',
  END = 'toTimestamp'
}

const useMatchers = (events: Ref<KrakenStakingEvents>) => {
  const { getAssetIdentifierForSymbol } = setupAssetInfoRetrieval();
  const { dateInputFormat } = setupSettings();
  return computed<SearchMatcher<KrakenStakingKeys, KrakenStakingValueKeys>[]>(
    () => [
      {
        key: KrakenStakingKeys.ASSET,
        keyValue: KrakenStakingValueKeys.ASSET,
        description: i18n.t('closed_trades.filter.base_asset').toString(),
        suggestions: () => events.value.assets,
        validate: (asset: string) => events.value.assets.includes(asset),
        transformer: (asset: string) =>
          getAssetIdentifierForSymbol(asset) ?? asset
      },
      {
        key: KrakenStakingKeys.TYPE,
        keyValue: KrakenStakingValueKeys.TYPE,
        description: i18n.t('closed_trades.filter.quote_asset').toString(),
        suggestions: () => KrakenStakingEventType.options,
        validate: (option: string) =>
          KrakenStakingEventType.options.includes(option as any)
      },
      {
        key: KrakenStakingKeys.START,
        keyValue: KrakenStakingValueKeys.START,
        description: i18n.t('closed_trades.filter.start_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('closed_trades.filter.date_hint', {
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
        key: KrakenStakingKeys.END,
        keyValue: KrakenStakingValueKeys.END,
        description: i18n.t('closed_trades.filter.end_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('closed_trades.filter.date_hint', {
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
      }
    ]
  );
};

export default defineComponent({
  name: 'KrakenStakingEvents',
  components: { TableFilter, RefreshButton, UpgradeRow },
  props: {
    events: {
      required: true,
      type: Object as PropType<KrakenStakingEvents>
    },
    loading: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  emit: ['update:pagination', 'refresh'],
  setup(props, { emit }) {
    const { events } = toRefs(props);
    const filters: Ref<MatchedKeyword<KrakenStakingValueKeys>> = ref({});

    const { itemsPerPage } = setupSettings();
    const { isMobile } = setupThemeCheck();

    const options = ref<KrakenStakingPaginationOptions>({
      page: 1,
      itemsPerPage: unref(itemsPerPage),
      sortBy: ['timestamp'],
      sortDesc: [true]
    });

    const showUpgradeRow = computed(() => {
      const { entriesLimit, entriesTotal } = events.value;
      return entriesLimit <= entriesTotal && entriesLimit > 0;
    });

    const updatePagination = ({
      itemsPerPage,
      page,
      sortBy,
      sortDesc
    }: KrakenStakingPaginationOptions) => {
      const { asset, eventSubtypes, fromTimestamp, toTimestamp } =
        filters.value;
      const pagination: KrakenStakingPagination = {
        ascending: sortDesc[0],
        orderByAttribute: sortBy[0],
        limit: itemsPerPage,
        offset: (page - 1) * itemsPerPage,
        fromTimestamp: fromTimestamp,
        toTimestamp: toTimestamp,
        eventSubtypes: eventSubtypes ? [eventSubtypes] : undefined,
        asset: asset
      };
      emit('update:pagination', pagination);
    };

    const updateFilter = (matchers: MatchedKeyword<KrakenStakingValueKeys>) => {
      filters.value = matchers;
      options.value = { ...options.value, page: 1 };
    };

    const refresh = () => emit('refresh');

    watch(options, options => updatePagination(options));

    return {
      options,
      isMobile,
      showUpgradeRow,
      tableHeaders: getHeaders(),
      matchers: useMatchers(events),
      refresh,
      updateFilter
    };
  }
});
</script>
