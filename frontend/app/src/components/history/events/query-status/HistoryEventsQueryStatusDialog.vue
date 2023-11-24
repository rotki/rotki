<script setup lang="ts">
import { type HistoryEventsQueryData } from '@/types/websocket-messages';

const props = withDefaults(
  defineProps<{
    locations?: string[];
  }>(),
  {
    locations: () => []
  }
);

const { locations } = toRefs(props);

const { t } = useI18n();

const { sortedQueryStatus, getKey } = useEventsQueryStatus(locations);

const showTooltip = (item: HistoryEventsQueryData) => !!item.period;
</script>

<template>
  <QueryStatusDialog
    :get-key="getKey"
    :items="sortedQueryStatus"
    :show-tooltip="showTooltip"
  >
    <template #title>
      {{ t('transactions.query_status_events.title') }}
    </template>

    <template #current>
      <HistoryEventsQueryStatusCurrent :locations="locations" />
    </template>

    <template #item="{ item }">
      <LocationIcon icon :item="item.location" size="20px" />
      <HistoryEventsQueryStatusLine :item="item" class="ms-2" />
    </template>

    <template #tooltip="{ item }">
      <i18n
        :path="
          item.period[0] === 0
            ? 'transactions.query_status_events.latest_period_end_date'
            : 'transactions.query_status_events.latest_period_date_range'
        "
      >
        <template #start>
          <DateDisplay :timestamp="item.period[0]" />
        </template>
        <template #end>
          <DateDisplay :timestamp="item.period[1]" />
        </template>
      </i18n>
    </template>
  </QueryStatusDialog>
</template>
