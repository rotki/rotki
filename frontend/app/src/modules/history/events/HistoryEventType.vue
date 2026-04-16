<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';
import type { HistoryEventEntry, HistoryEventState } from '@/modules/history/events/schemas';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import HistoryEventStateChip from '@/modules/history/events/HistoryEventStateChip.vue';
import HistoryEventTypeCombination from '@/modules/history/events/HistoryEventTypeCombination.vue';
import HistoryEventTypeCounterparty from '@/modules/history/events/HistoryEventTypeCounterparty.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

const { event, groupLocationLabel, icon, highlight, hideStateChips } = defineProps<{
  event: HistoryEventEntry;
  groupLocationLabel?: string;
  icon?: RuiIcons;
  highlight?: boolean;
  hideStateChips?: boolean;
}>();

const { getEventTypeData } = useHistoryEventMappings();
const attrs = getEventTypeData(() => event);

const isInformational = computed<boolean>(() => event.eventType === 'informational');

const eventStates = computed<HistoryEventState[]>(() => event.states ?? []);

const showLocationLabel = computed<boolean>(() => {
  const eventLabel = event.locationLabel;
  if (!eventLabel)
    return false;

  // Show only when different from group (or no group context)
  return !groupLocationLabel || eventLabel !== groupLocationLabel;
});
</script>

<template>
  <div
    data-cy="event-type"
    class="flex items-center text-left min-w-0"
  >
    <HistoryEventTypeCounterparty
      v-if="('counterparty' in event && event.counterparty) || ('address' in event && event.address)"
      :counterparty="event.counterparty || undefined"
      :address="event.address || undefined"
      :location="event.location"
      class="shrink-0"
    >
      <HistoryEventTypeCombination
        :highlight="highlight"
        :icon="icon"
        :type="attrs"
        :show-info="isInformational"
      />
    </HistoryEventTypeCounterparty>
    <HistoryEventTypeCombination
      v-else
      :highlight="highlight"
      :icon="icon"
      :type="attrs"
      :show-info="isInformational"
      class="shrink-0"
    />

    <div class="ml-3 min-w-0">
      <div class="font-medium uppercase text-sm truncate">
        {{ attrs.label }}
      </div>
      <HistoryEventAccount
        v-if="showLocationLabel"
        :location="event.location"
        :location-label="event.locationLabel!"
        class="text-rui-text-secondary"
      />
      <div
        v-if="eventStates.length > 0 && !hideStateChips"
        class="flex flex-wrap gap-0.5"
      >
        <HistoryEventStateChip
          v-for="state in eventStates"
          :key="state"
          :state="state"
        />
      </div>
    </div>
  </div>
</template>
