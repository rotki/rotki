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
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import ValueAccuracyHint from '@/components/helper/hint/ValueAccuracyHint.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import TableFilter from '@/components/history/filtering/TableFilter.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useKrakenStakingFilter } from '@/composables/filters/kraken-staking';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useKrakenStakingEventTypes } from '@/store/staking/consts';
import {
  KrakenStakingEvents,
  KrakenStakingEventType,
  KrakenStakingPagination,
  KrakenStakingPaginationOptions
} from '@/types/staking';

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

const { itemsPerPage } = storeToRefs(useFrontendSettingsStore());
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { krakenStakingEventTypeData } = useKrakenStakingEventTypes();

const options = ref<KrakenStakingPaginationOptions>({
  page: 1,
  itemsPerPage: get(itemsPerPage),
  sortBy: [],
  sortDesc: []
});

const { t, tc } = useI18n();

const showUpgradeRow = computed(() => {
  const { entriesLimit, entriesTotal } = get(events);
  return entriesLimit <= entriesTotal && entriesLimit > 0;
});

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

const { filters, matchers, updateFilter } = useKrakenStakingFilter();

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

const refresh = () => emit('refresh');

const getEventTypeLabel = (eventType: KrakenStakingEventType) => {
  return (
    get(krakenStakingEventTypeData).find(data => data.identifier === eventType)
      ?.label ?? eventType
  );
};

watch(filters, () => {
  set(options, { ...get(options), page: 1 });
});

watch(options, options => updatePagination(options));
</script>
