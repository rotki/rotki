<script setup lang="ts">
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import BadgeDisplay from '@/modules/history/BadgeDisplay.vue';
import HistoryEventAsset from '@/modules/history/events/HistoryEventAsset.vue';
import ShowInEventsButton from '@/modules/history/events/ShowInEventsButton.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';

defineProps<{
  entry: HistoryEventEntry;
  typeLabel: string;
}>();

const emit = defineEmits<{
  'show-in-events': [];
}>();
</script>

<template>
  <div
    class="flex flex-col gap-1 rounded-sm border border-rui-warning/40 bg-rui-warning/10 p-2"
    data-testid="potential-match-subject"
  >
    <div class="flex flex-wrap items-center gap-x-1.5 gap-y-1">
      <BadgeDisplay class="normal-case!">
        {{ typeLabel }}
      </BadgeDisplay>
      <LocationDisplay
        size="16px"
        :identifier="entry.location"
        horizontal
        dense
      />
      <DateDisplay
        class="ml-auto text-caption text-rui-text-disabled"
        :timestamp="entry.timestamp"
        milliseconds
      />
    </div>

    <div class="flex items-center justify-between gap-2">
      <HistoryEventAsset
        dense
        inline
        disable-options
        :event="entry"
      />
      <ShowInEventsButton @click="emit('show-in-events')" />
    </div>
  </div>
</template>
