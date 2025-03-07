<script setup lang="ts">
import type { HistoryEventsQueryData } from '@/types/websocket-messages';
import DateDisplay from '@/components/display/DateDisplay.vue';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventsQueryStatusLine from '@/components/history/events/query-status/HistoryEventsQueryStatusLine.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';

defineProps<{ item: HistoryEventsQueryData }>();
</script>

<template>
  <LazyLoader
    min-height="40px"
    class="flex items-center pl-0.5"
  >
    <LocationIcon
      icon
      :item="item.location"
      size="1.25rem"
    />
    <HistoryEventsQueryStatusLine
      :item="item"
      class="ms-2"
    />

    <RuiTooltip
      v-if="item.period"
      class="ml-2 cursor-pointer"
      :open-delay="400"
      tooltip-class="max-w-[12rem]"
    >
      <template #activator>
        <RuiIcon
          class="text-rui-text-secondary"
          name="lu-circle-help"
        />
      </template>

      <i18n-t
        :keypath="
          item.period[0] === 0
            ? 'transactions.query_status_events.latest_period_end_date'
            : 'transactions.query_status_events.latest_period_date_range'
        "
        tag="span"
      >
        <template #start>
          <DateDisplay :timestamp="item.period[0]" />
        </template>
        <template #end>
          <DateDisplay :timestamp="item.period[1]" />
        </template>
      </i18n-t>
    </RuiTooltip>
  </LazyLoader>
</template>
