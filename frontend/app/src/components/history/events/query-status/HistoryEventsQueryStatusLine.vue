<script setup lang="ts">
import type { HistoryEventsQueryData } from '@/types/websocket-messages';
import DateDisplay from '@/components/display/DateDisplay.vue';
import HashLink from '@/components/helper/HashLink.vue';
import { useEventsQueryStatus } from '@/composables/history/events/query-status/events-query-status';

defineProps<{ item: HistoryEventsQueryData }>();

const { getItemTranslationKey } = useEventsQueryStatus();
</script>

<template>
  <i18n-t
    :keypath="getItemTranslationKey(item)"
    tag="div"
    class="flex items-center py-2 text-no-wrap flex-wrap text-body-2"
  >
    <template #name>
      <div class="font-bold px-2 text-no-wrap">
        <HashLink
          :text="item.name"
          no-link
          :show-icon="false"
          :location="item.location"
          disable-scramble
        />
      </div>
    </template>
    <template #start>
      <div
        v-if="item.period"
        class="font-bold px-1 text-no-wrap"
      >
        <DateDisplay :timestamp="item.period[0]" />
      </div>
    </template>
    <template #end>
      <div
        v-if="item.period"
        class="font-bold px-1 text-no-wrap"
      >
        <DateDisplay :timestamp="item.period[1]" />
      </div>
    </template>
  </i18n-t>
</template>
