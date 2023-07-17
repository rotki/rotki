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
      <HistoryEventsQueryStatusCurrent
        :locations="locations"
        class="px-6 pb-4 text-caption"
      />
    </template>

    <template #item="{ item }">
      <LocationIcon icon no-padding :item="item.location" size="20px" />
      <HistoryEventsQueryStatusLine :item="item" class="ms-2" />
    </template>

    <template #tooltip="{ item }">
      <I18n
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
      </I18n>
    </template>
  </QueryStatusDialog>
</template>
