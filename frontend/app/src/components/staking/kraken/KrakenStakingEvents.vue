<template>
  <card outlined-body>
    <template #title>
      <refresh-button
        :loading="loading"
        :tooltip="tc('kraken_staking_events.refresh_tooltip')"
        @refresh="refresh"
      />
      {{ t('kraken_staking_events.titles') }}
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
      multi-sort
      :must-sort="false"
    >
      <template v-if="showUpgradeRow" #body.prepend="{ headers }">
        <upgrade-row
          :limit="events.entriesLimit"
          :total="events.entriesTotal"
          :colspan="headers.length"
          :label="tc('kraken_staking_events.upgrade.label')"
        />
      </template>
      <template #header.usdValue>
        {{
          t('common.value_in_symbol', {
            symbol: currencySymbol
          })
        }}
        <value-accuracy-hint />
      </template>
      <template #item.type="{ item }">
        <badge-display color="grey">
          {{ getEventTypeLabel(item.eventType) }}
        </badge-display>
      </template>
      <template #item.asset="{ item }">
        <asset-details :asset="item.asset" />
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display :value="item.usdValue" fiat-currency="USD" />
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
    </data-table>
  </card>
</template>

<script setup lang="ts">
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, PropType, Ref, ref, toRefs, watch } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { DataTableHeader } from 'vuetify';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useAssetInfoRetrieval } from '@/store/assets';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { krakenStakingEventTypeData } from '@/store/staking/consts';
import {
  KrakenStakingEvents,
  KrakenStakingEventType,
  KrakenStakingPagination,
  KrakenStakingPaginationOptions
} from '@/types/staking';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';

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

const getEventTypeIdentifier = (label: string) => {
  return (
    get(krakenStakingEventTypeData).find(data => data.label === label)
      ?.identifier ?? label
  );
};

const { t, tc } = useI18n();

const useMatchers = (events: Ref<KrakenStakingEvents>) => {
  const { getAssetIdentifierForSymbol } = useAssetInfoRetrieval();
  const { dateInputFormat } = storeToRefs(useFrontendSettingsStore());
  return computed<SearchMatcher<KrakenStakingKeys, KrakenStakingValueKeys>[]>(
    () => {
      const krakenStakingEventTypeValues = get(krakenStakingEventTypeData).map(
        data => data.label
      );

      return [
        {
          key: KrakenStakingKeys.ASSET,
          keyValue: KrakenStakingValueKeys.ASSET,
          description: t('kraken_staking_events.filter.asset').toString(),
          suggestions: () => get(events).assets,
          validate: (asset: string) => get(events).assets.includes(asset),
          transformer: (asset: string) =>
            getAssetIdentifierForSymbol(asset) ?? asset
        },
        {
          key: KrakenStakingKeys.TYPE,
          keyValue: KrakenStakingValueKeys.TYPE,
          description: t('kraken_staking_events.filter.type').toString(),
          suggestions: () => krakenStakingEventTypeValues,
          validate: (option: string) =>
            krakenStakingEventTypeValues.includes(option as any),
          transformer: (type: string) => getEventTypeIdentifier(type)
        },
        {
          key: KrakenStakingKeys.START,
          keyValue: KrakenStakingValueKeys.START,
          description: t('kraken_staking_events.filter.start_date').toString(),
          suggestions: () => [],
          hint: t('kraken_staking_events.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          }).toString(),
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
          key: KrakenStakingKeys.END,
          keyValue: KrakenStakingValueKeys.END,
          description: t('kraken_staking_events.filter.end_date').toString(),
          suggestions: () => [],
          hint: t('kraken_staking_events.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          }).toString(),
          validate: value => {
            return (
              value.length > 0 &&
              !isNaN(convertToTimestamp(value, get(dateInputFormat)))
            );
          },
          transformer: (date: string) =>
            convertToTimestamp(date, get(dateInputFormat)).toString()
        }
      ];
    }
  );
};

const props = defineProps({
  events: {
    required: true,
    type: Object as PropType<KrakenStakingEvents>
  },
  loading: {
    required: false,
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:pagination', 'refresh']);
const { events } = toRefs(props);
const filters: Ref<MatchedKeyword<KrakenStakingValueKeys>> = ref({});

const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const options = ref<KrakenStakingPaginationOptions>({
  page: 1,
  itemsPerPage: get(itemsPerPage),
  sortBy: [],
  sortDesc: []
});

const showUpgradeRow = computed(() => {
  const { entriesLimit, entriesTotal } = get(events);
  return entriesLimit <= entriesTotal && entriesLimit > 0;
});

const updatePagination = ({
  itemsPerPage,
  page,
  sortBy,
  sortDesc
}: KrakenStakingPaginationOptions) => {
  const { asset, eventSubtypes, fromTimestamp, toTimestamp } = get(filters);
  const pagination: KrakenStakingPagination = {
    orderByAttributes: sortBy.length > 0 ? sortBy : ['timestamp'],
    ascending: sortDesc.length > 0 ? sortDesc.map(bool => !bool) : [false],
    limit: itemsPerPage,
    offset: (page - 1) * itemsPerPage,
    fromTimestamp: fromTimestamp as string,
    toTimestamp: toTimestamp as string,
    eventSubtypes: eventSubtypes ? [eventSubtypes as string] : undefined,
    asset: (asset as string) || undefined
  };
  emit('update:pagination', pagination);
};

const updateFilter = (matchers: MatchedKeyword<KrakenStakingValueKeys>) => {
  set(filters, matchers);
  set(options, { ...get(options), page: 1 });
};

const refresh = () => emit('refresh');

watch(options, options => updatePagination(options));

const getEventTypeLabel = (eventType: KrakenStakingEventType) => {
  return (
    get(krakenStakingEventTypeData).find(data => data.identifier === eventType)
      ?.label ?? eventType
  );
};

const matchers = useMatchers(events);

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.event').toString(),
    value: 'type'
  },
  {
    text: t('common.asset').toString(),
    value: 'asset'
  },
  {
    text: t('common.datetime').toString(),
    value: 'timestamp'
  },
  {
    text: t('common.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    value: 'usdValue',
    align: 'end'
  }
]);
</script>
