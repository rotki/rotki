<script setup lang="ts">
import type { Blockchain } from '@rotki/common';
import type { RuiIcons } from '@rotki/ui-library';
import type { HistoryEventEntry, HistoryEventState } from '@/types/history/events/schemas';
import HistoryEventAccount from '@/components/history/events/HistoryEventAccount.vue';
import HistoryEventStateChip from '@/components/history/events/HistoryEventStateChip.vue';
import HistoryEventTypeCombination from '@/components/history/events/HistoryEventTypeCombination.vue';
import HistoryEventTypeCounterparty from '@/components/history/events/HistoryEventTypeCounterparty.vue';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';

const props = defineProps<{
  event: HistoryEventEntry;
  chain: Blockchain;
  groupLocationLabel?: string;
  icon?: RuiIcons;
  highlight?: boolean;
  hideStateChips?: boolean;
}>();

const { event } = toRefs(props);

const { getEventTypeData } = useHistoryEventMappings();
const attrs = getEventTypeData(event);

const isInformational = computed<boolean>(() => get(event).eventType === 'informational');

const eventStates = computed<HistoryEventState[]>(() => get(event).states ?? []);

const showLocationLabel = computed<boolean>(() => {
  const eventLabel = get(event).locationLabel;
  if (!eventLabel)
    return false;

  const groupLabel = props.groupLocationLabel;
  // Show only when different from group (or no group context)
  return !groupLabel || eventLabel !== groupLabel;
});
</script>

<template>
  <div class="flex items-center text-left">
    <HistoryEventTypeCounterparty
      v-if="('counterparty' in event && event.counterparty) || ('address' in event && event.address)"
      :counterparty="event.counterparty || undefined"
      :address="event.address || undefined"
      :location="event.location"
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
    />

    <div class="ml-3.5">
      <div class="font-medium uppercase text-sm">
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
